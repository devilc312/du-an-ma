# Hướng dẫn hoạt động và vận hành Todo AI

Tài liệu này mô tả luồng chạy thực tế, cách quản trị, backup, xử lý lỗi và triển khai production.

## 1. Kiến trúc hoạt động

```text
Browser (React/Tailwind)
  ├─ HTTPS/REST ──> FastAPI ──SQLAlchemy Async──> PostgreSQL
  └─ WSS ─────────> FastAPI WebSocket <──Pub/Sub── Redis
                                     ^
Reminder worker ── query/insert ─────┘
        └─ Redis distributed lock
FastAPI AI service ──> Anthropic API (nếu có key)
                   └─> rule-based fallback (nếu không có key)
```

- PostgreSQL là nguồn dữ liệu chính: user, role, token hash, Todo, notification, AI history và audit.
- Redis không phải nguồn dữ liệu bền vững. Nó dùng cho rate limit, lock worker và truyền notification realtime.
- Frontend dùng TanStack Query giữ cache; mutation thành công sẽ invalidate Todo. WebSocket cập nhật cache notification ngay lập tức; polling 30 giây là fallback.

## 2. Luồng đăng ký và đăng nhập

### Đăng ký

1. Frontend validate email, tên và mật khẩu.
2. `POST /auth/register` rate-limit theo IP.
3. Backend kiểm tra email trùng, hash mật khẩu bằng Argon2.
4. Backend gọi `default_user_role`; payload không có field role nên client không thể tự gửi quyền.
5. User được tạo với duy nhất role `user`.
6. API trả access token 15 phút và refresh token 30 ngày.

### Đăng nhập và refresh

1. Login kiểm tra Argon2 và `is_active`.
2. Access token gửi qua `Authorization: Bearer ...`.
3. Khi API trả 401, Axios chỉ chạy một refresh request cho các request đồng thời.
4. Refresh token cũ bị revoke, token mới được phát (rotation).
5. Logout revoke refresh token đang dùng.

### Lưu ý production

Phiên bản này lưu token phía web để demo/deploy độc lập đơn giản. Khi ứng dụng public có rủi ro XSS cao, chuyển refresh token sang cookie `HttpOnly; Secure; SameSite` và thêm CSRF token.

## 3. Phân quyền

- `user`: quản lý dữ liệu của chính tài khoản.
- `admin`: có thêm route `/admin/*` để xem user, đổi role và khóa tài khoản.
- Seed tạo 2 role và admin đầu tiên.
- Backend không cho:
  - user thường gọi admin API;
  - user tự truyền role lúc đăng ký;
  - admin tự khóa tài khoản đang dùng;
  - khóa hoặc gỡ quyền admin hoạt động cuối cùng.
- Mọi thao tác role/status được ghi `audit_logs`.

### Cấp admin

Đăng nhập admin đầu tiên, vào **Quản trị**, bấm badge `User`, xác nhận. UI gửi tập role `['user', 'admin']`.

### Thêm role mới

Hiện UI hỗ trợ `user/admin`. Để thêm role nghiệp vụ:

1. Thêm role qua migration/seed.
2. Xác định dependency/permission cho route.
3. Mở rộng union `Role` ở frontend.
4. Mở rộng giao diện Admin chọn nhiều role.

## 4. Todo CRUD

- **Create:** form gửi title, description, status, priority, timestamps ISO, category ID, tag names.
- **Read:** API luôn thêm filter `Todo.user_id == current_user.id`, sau đó search/filter/sort/page.
- **Update:** chỉ tải Todo thuộc user. Khi chuyển `completed`, backend đặt `completed_at`; khi mở lại sẽ xóa timestamp.
- **Delete:** UI hỏi xác nhận, backend kiểm tra ownership rồi xóa cascade notification liên quan.
- **Tags:** tên được trim, lowercase, deduplicate; tag chưa có được tạo cho user.
- **Category:** API kiểm tra category thuộc đúng user trước khi gắn.

## 5. Ngày giờ và nhắc việc realtime

- Browser gửi giờ từ `datetime-local`, frontend chuyển thành ISO UTC.
- PostgreSQL dùng `TIMESTAMP WITH TIME ZONE`.
- `users.timezone` lưu timezone IANA cho định dạng/nâng cấp lịch sau này.
- Đồng hồ UI cập nhật mỗi giây bằng `useClock`.

### Worker

1. `worker` chạy vòng lặp mỗi 30 giây.
2. Lấy Redis lock `worker:reminders` để chỉ một instance xử lý.
3. Query Todo chưa complete/archive, chưa gửi reminder và nằm trong window.
4. `FOR UPDATE SKIP LOCKED` tránh tranh chấp DB.
5. Tạo bản ghi notification và đánh dấu `reminder_sent_at`.
6. Publish JSON vào channel `notifications:{user_id}`.
7. WebSocket subscribe channel đúng user và đẩy tới browser.
8. Nếu user offline, bản ghi PostgreSQL vẫn xuất hiện lần sau.

Đổi khoảng nhắc bằng `REMINDER_WINDOW_MINUTES`; sau khi đổi phải restart API/worker.

## 6. Trợ lý AI

### Khi có Anthropic key

- Đặt `ANTHROPIC_API_KEY` và `ANTHROPIC_MODEL`.
- `AIService.chat` gửi system prompt tiếng Việt, history tối đa 10 message gần nhất.
- `suggest` yêu cầu JSON có schema: summary, description, subtasks, priority, tips.
- Nếu model trả JSON lỗi, hệ thống tự fallback.

### Khi không có key

- App vẫn chạy.
- Chat trả hướng dẫn theo keyword và nguyên tắc quản lý thời gian.
- Suggest tạo checklist chung, chọn priority theo việc có deadline hay không.
- Response trả `provider: fallback` để có thể hiển thị/giám sát.

### Đổi provider AI

Tạo implementation mới cùng interface trong `backend/app/services/ai.py`:

```python
async def chat(message, history) -> AIResult: ...
async def suggest(title, description, due_at) -> dict: ...
```

Giữ validate output ở server; không để model tự gọi CRUD mà không có bước xác nhận rõ ràng.

## 7. Migration và seed

```bash
cd backend
alembic upgrade head
python -m app.seed
```

Tạo migration mới sau khi đổi model:

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

Luôn review file migration, đặc biệt default, enum, index và downgrade trước khi chạy production.

Seed là idempotent: chạy lại không tạo role/user trùng, và sẽ bổ sung role admin cho `ADMIN_EMAIL` nếu cần.

## 8. Backup và restore

### Backup PostgreSQL

```bash
docker compose exec postgres pg_dump -U todo -Fc todo > todo-backup.dump
```

### Restore vào database trống

```bash
docker compose exec -T postgres pg_restore -U todo -d todo --clean --if-exists < todo-backup.dump
```

### Redis

Notification đã nằm PostgreSQL nên mất Redis không làm mất nghiệp vụ chính. Redis volume chỉ cần giữ nếu muốn giữ counter/append-only state tạm thời.

## 9. Quan sát và kiểm tra sức khỏe

- `/health`: process API còn phản hồi.
- `/ready`: kiểm tra kết nối cả PostgreSQL và Redis.
- `docker compose logs -f api worker`: xem log.
- Swagger `/docs`: thử route với Bearer token.

Nên bổ sung khi production: structured JSON logs, request ID, Prometheus metrics, Sentry/OpenTelemetry, dashboard latency/error/worker lag.

## 10. Xử lý lỗi thường gặp

### `SECRET_KEY must have at least 32 characters`

Tạo secret mạnh và cập nhật `.env`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### API không kết nối DB

- Trong Docker hostname phải là `postgres`, không phải `localhost`.
- Chạy `docker compose ps` và xem health của Postgres.
- Kiểm tra user/password/database trong `DATABASE_URL`.

### Không có notification realtime

1. Kiểm tra worker đang chạy.
2. Kiểm tra Redis `/ready`.
3. Xem `VITE_WS_URL` dùng `ws://` local hoặc `wss://` production.
4. Reverse proxy phải hỗ trợ `Upgrade` và `Connection` cho WebSocket.
5. Notification vẫn phải xuất hiện tối đa sau chu kỳ polling 30 giây.

### AI luôn fallback

- `ANTHROPIC_API_KEY` đang trống/sai hoặc `AI_ENABLED=false`.
- Kiểm tra model ID và quyền account.
- Restart API sau khi đổi env.

### Timezone không hợp lệ trên Windows

Cài dependency `tzdata` (đã có trong `pyproject.toml`) và dùng tên IANA như `Asia/Ho_Chi_Minh`, không dùng `GMT+7`.

### Migration lỗi enum/schema

Không xóa volume production. Backup DB, xem revision hiện tại bằng `alembic current`, sửa migration forward và thử trên bản copy dữ liệu.

## 11. Triển khai production

Checklist tối thiểu:

- [ ] Secret/người dùng DB/mật khẩu admin mạnh, lưu trong secret manager.
- [ ] HTTPS/WSS qua reverse proxy; CORS chỉ cho domain thật.
- [ ] Không publish port PostgreSQL/Redis ra Internet.
- [ ] PostgreSQL backup tự động và restore drill.
- [ ] Chạy migration một lần trước khi rolling API.
- [ ] API và worker chạy user không phải root, resource limit.
- [ ] Nginx/CDN phục vụ web, cache asset hash.
- [ ] Log, alert `/ready`, disk, DB connections, worker failures.
- [ ] Chính sách retention cho refresh token, audit log và AI history.
- [ ] Review privacy trước khi gửi mô tả Todo cho AI provider.

### Reverse proxy WebSocket (ý tưởng)

```nginx
location /api/ {
  proxy_pass http://api:8000;
  proxy_http_version 1.1;
  proxy_set_header Upgrade $http_upgrade;
  proxy_set_header Connection "upgrade";
  proxy_set_header Host $host;
}
```

## 12. Quy trình cập nhật an toàn

1. Chạy test/lint/build.
2. Backup DB.
3. Build immutable image/tag.
4. Chạy migration job.
5. Deploy API rồi worker/web.
6. Kiểm tra `/health`, `/ready`, login, CRUD, WebSocket.
7. Rollback image nếu lỗi; không downgrade DB nếu migration đã phá hủy dữ liệu.

Lệnh xác minh chuẩn:

```bash
python -m pytest backend/tests -q
python -m ruff check backend
npm --prefix frontend test
npm --prefix frontend run lint
npm --prefix frontend run build
```
