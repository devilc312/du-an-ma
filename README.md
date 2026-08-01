# Todo AI — FastAPI, PostgreSQL, Redis, React

Ứng dụng quản lý công việc full-stack gồm tài khoản, phân quyền `user/admin`, Todo, thông báo sắp đến hạn theo thời gian thực và trợ lý AI dùng Anthropic hoặc chế độ fallback không cần API key.

> **Trạng thái hiện tại (01/08/2026):** dự án đã hoàn chỉnh cho development/demo local bằng Docker, với auth cookie HttpOnly + CSRF, migration đồng bộ, UI các luồng chính và test regression. Chưa nên public trực tiếp lên Internet trước khi hoàn thành các mục production-only trong phần [Việc còn lại](#việc-còn-lại-và-lỗi-đã-biết).

## 1. Tính năng đã có

- Đăng ký, đăng nhập, refresh-token rotation, đăng xuất và cập nhật hồ sơ.
- Tài khoản mới mặc định có role `user`; API quản trị được bảo vệ bằng role `admin`.
- Admin xem tài khoản, cấp/thu hồi quyền, khóa/mở tài khoản và không thể vô hiệu hóa admin hoạt động cuối cùng.
- Todo CRUD, tìm kiếm, trạng thái, ưu tiên, deadline, reminder, category, tags và phân trang ở backend.
- Notification được lưu trong PostgreSQL, Redis Pub/Sub và WebSocket phục vụ realtime.
- Reminder worker chạy độc lập và dùng Redis lock để hạn chế xử lý trùng.
- AI gợi ý Todo và chat bằng Anthropic; khi không có API key sẽ dùng fallback rule-based.
- OpenAPI tại `/docs`, liveness tại `/health`, readiness tại `/ready`.
- Docker Compose chạy PostgreSQL, Redis, API, worker và frontend.

Một số API backend như category, statistics, filter nâng cao và trạng thái `archived` chưa có UI đầy đủ. Xem [Việc còn lại](#việc-còn-lại-và-lỗi-đã-biết).

## 2. Stack

| Tầng | Công nghệ |
|---|---|
| API | Python 3.12+, FastAPI, Pydantic |
| Data | PostgreSQL 17, SQLAlchemy 2 Async, asyncpg, Alembic |
| Cache/realtime | Redis 7.4, Pub/Sub, distributed lock, WebSocket |
| Auth | Argon2, JWT access token, opaque hashed refresh token |
| AI | Anthropic async SDK + fallback |
| Web | React 19, TypeScript, Vite 7, Tailwind CSS 4, TanStack Query |
| Test | pytest, Ruff, Vitest, Testing Library, ESLint |
| Runtime | Docker Compose, Nginx |

## 3. Yêu cầu cài đặt

### Cách A — Docker (khuyến nghị)

Cần cài:

- **Docker Desktop** có Docker Compose v2.
- Windows: bật virtualization và dùng backend **WSL2** của Docker Desktop.
- Git chỉ cần nếu tải dự án bằng `git clone`.
- Tối thiểu nên có khoảng 4 GB RAM trống và 5 GB dung lượng đĩa cho image/volume.

Kiểm tra sau khi cài:

```powershell
docker --version
docker compose version
docker info
```

Cài nhanh bằng `winget` trên Windows nếu máy chưa có Docker/Git:

```powershell
winget install -e --id Docker.DockerDesktop
winget install -e --id Git.Git
```

Sau khi cài Docker Desktop, mở ứng dụng và chờ Docker Engine chạy trước khi dùng `docker compose`.

### Cách B — Chạy source trực tiếp

Cần cài:

- **Python `>=3.12,<3.15`**; khuyến nghị Python 3.12 hoặc 3.13.
- **Node.js 22.12+ hoặc Node.js 24 LTS** và npm.
- **PostgreSQL 17**.
- **Redis 7.x**. Redis không có bản native Windows chính thức phù hợp cho development hiện đại; trên Windows nên chạy Redis bằng Docker hoặc WSL2.

Cài Python và Node.js LTS bằng `winget`:

```powershell
winget install -e --id Python.Python.3.12
winget install -e --id OpenJS.NodeJS.LTS
```

Mở terminal mới rồi kiểm tra:

```powershell
python --version
node --version
npm --version
```

### Các cổng cần trống

| Cổng | Dịch vụ |
|---:|---|
| `5432` | PostgreSQL |
| `6379` | Redis |
| `8000` | FastAPI |
| `8080` | Frontend chạy bằng Docker/Nginx |
| `5173` | Frontend chạy bằng Vite development |

`ANTHROPIC_API_KEY` là tùy chọn. Nếu để trống, ứng dụng vẫn chạy nhưng AI dùng fallback rule-based.

## 4. Cài đặt và chạy bằng Docker

### Bước 1 — Mở terminal tại đúng thư mục gốc

File Compose chuẩn của toàn dự án là:

```text
D:\Dự án ma\compose.yaml
```

PowerShell:

```powershell
cd "D:\Dự án ma"
docker compose config --quiet
```

Không chạy `docker compose` từ `C:\Users\cuong` vì ở đó không có `compose.yaml`. Không dùng `backend/docker-compose.yml` để khởi động toàn bộ dự án; đây là cấu hình backend phụ và hiện chưa đồng bộ đầy đủ với stack chính.

### Bước 2 — Tạo file môi trường

Chỉ sao chép file mẫu nếu `.env` chưa tồn tại.

PowerShell:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
```

Linux/macOS/Git Bash:

```bash
[ -f .env ] || cp .env.example .env
```

Trong `.env`, bắt buộc thay ít nhất:

```dotenv
SECRET_KEY=<random-secret-toi-thieu-32-ky-tu>
ADMIN_EMAIL=<email-admin>
ADMIN_PASSWORD=<mat-khau-admin-manh>
```

Tạo `SECRET_KEY` bằng Python:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Nếu chỉ cài Docker và không có Python, tạo secret bằng PowerShell:

```powershell
$bytes = New-Object byte[] 48
[Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
[Convert]::ToBase64String($bytes)
```

Lưu ý:

- Không commit `.env`; `.gitignore` đã bỏ qua file này.
- `.env.example` chỉ là template local và không được dùng nguyên trạng cho production.
- Các credentials từng có trong `.env` hiện tại phải được **rotate trước khi public/deploy**.
- Khi chạy trong Docker, `DATABASE_URL` phải dùng hostname `postgres` và `REDIS_URL` phải dùng hostname `redis`, không dùng `localhost`.

### Bước 3 — Build và khởi động

```powershell
docker compose up -d --build
```

API container sẽ chạy migration và seed admin trước khi khởi động Uvicorn. Worker được chạy bằng service riêng.

Kiểm tra trạng thái:

```powershell
docker compose ps
docker compose logs --tail 100 api worker
```

Các service `postgres` và `redis` phải ở trạng thái `healthy`; `api`, `worker`, `web` phải ở trạng thái `Up`.

### Bước 4 — Kiểm tra ứng dụng

PowerShell:

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/ready
```

Hoặc:

```powershell
curl.exe -f http://localhost:8000/health
curl.exe -f http://localhost:8000/ready
```

Địa chỉ sử dụng:

- Web: <http://localhost:8080>
- API: <http://localhost:8000>
- Swagger/OpenAPI: <http://localhost:8000/docs>
- Admin đầu tiên: `ADMIN_EMAIL` và `ADMIN_PASSWORD` trong `.env`.

### Các lệnh Docker thường dùng

```powershell
# Xem log liên tục
docker compose logs -f api worker web

# Restart các service
docker compose restart

# Build lại sau khi đổi dependency/image
docker compose up -d --build

# Dừng và xóa container/network, giữ dữ liệu DB
docker compose down

# Xem các service
docker compose ps
```

Reset toàn bộ dữ liệu local:

```powershell
docker compose down -v
docker compose up -d --build
```

> **Cảnh báo:** `docker compose down -v` xóa PostgreSQL và Redis volumes của dự án. Không dùng lệnh này với dữ liệu cần giữ hoặc môi trường production.

## 5. Development: database/Redis bằng Docker, app chạy native

Đây là cách thuận tiện để debug Python/React mà không phải cài PostgreSQL và Redis trực tiếp trên Windows.

### Bước 1 — Chạy hạ tầng

Từ thư mục gốc:

```powershell
cd "D:\Dự án ma"
docker compose up -d postgres redis
docker compose ps
```

### Bước 2 — Cấu hình backend native

Backend resolve `.env` cố định từ thư mục gốc dự án, không phụ thuộc current working directory. Khi chạy app native nhưng PostgreSQL/Redis ở Docker, đặt URL native trong biến môi trường của terminal để override root `.env` mà không tạo thêm file secret:

```powershell
cd "D:\Dự án ma\backend"
$env:DATABASE_URL="postgresql+asyncpg://todo:todo@localhost:5432/todo"
$env:REDIS_URL="redis://localhost:6379/0"
```

Giữ `SECRET_KEY`, `ADMIN_EMAIL` và `ADMIN_PASSWORD` trong root `.env`; không commit file này.

### Bước 3 — Cài và chạy backend

PowerShell:

```powershell
cd "D:\Dự án ma\backend"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Nếu PowerShell chặn script activate, có thể chạy trực tiếp executable mà không activate:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.seed
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Linux/macOS/Git Bash:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Chạy reminder worker ở terminal thứ hai, cũng tại thư mục `backend` và cùng virtual environment:

```powershell
.\.venv\Scripts\python.exe -m app.workers.reminders
```

### Bước 4 — Cài và chạy frontend

Vite chạy từ `frontend` nên không tự đọc `.env` ở root. Tạo `frontend/.env.local`. Vì Vite chạy ở `5173` còn API native ở `8000`, cookie auth hoạt động qua CORS credentials; WebSocket dùng ticket một lần:

```powershell
cd "D:\Dự án ma\frontend"
@"
VITE_API_URL=http://localhost:8000/api/v1
VITE_WS_URL=ws://localhost:8000/api/v1/ws/notifications
"@ | Set-Content .env.local
npm ci
npm run dev
```

Mở <http://localhost:5173>.

Nếu dùng Bash:

```bash
cd frontend
cat > .env.local <<'EOF'
VITE_API_URL=http://localhost:8000/api/v1
VITE_WS_URL=ws://localhost:8000/api/v1/ws/notifications
EOF
npm ci
npm run dev
```

## 6. Development hoàn toàn không dùng Docker

Cài PostgreSQL 17 và Redis 7.x, tạo database/user PostgreSQL tương ứng. Ví dụ chạy bằng tài khoản quản trị trong `psql`:

```sql
CREATE USER todo WITH PASSWORD 'replace-with-a-local-db-password';
CREATE DATABASE todo OWNER todo;
```

Sau đó cập nhật root `.env` hoặc export biến môi trường trước khi chạy backend:

```dotenv
DATABASE_URL=postgresql+asyncpg://todo:<url-encoded-password>@localhost:5432/todo
REDIS_URL=redis://localhost:6379/0
```

Nếu mật khẩu có ký tự đặc biệt, phải URL-encode phần mật khẩu trong `DATABASE_URL`. Sau đó làm tiếp các bước migration, seed, backend, worker và frontend ở phần trên.

Trên Windows, cách hybrid dùng Docker cho PostgreSQL/Redis vẫn được khuyến nghị vì Redis native không được dự án kiểm chứng.

## 7. Biến môi trường

| Biến | Bắt buộc | Ý nghĩa |
|---|---:|---|
| `APP_NAME` | Không | Tên hiển thị của API |
| `ENVIRONMENT` | Có khi deploy | Môi trường `development`/production; production validation còn cần hoàn thiện |
| `API_V1_PREFIX` | Không | Prefix API, mặc định `/api/v1` |
| `SECRET_KEY` | Có | Khóa ký JWT, tối thiểu 32 ký tự; phải là random secret |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Không | Thời hạn access token |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Không | Thời hạn refresh token |
| `DATABASE_URL` | Có | PostgreSQL async URL `postgresql+asyncpg://...` |
| `REDIS_URL` | Có | Redis cho rate limit, lock và realtime |
| `CORS_ORIGINS` | Có | Danh sách origin cách nhau bằng dấu phẩy |
| `DEFAULT_TIMEZONE` | Không | Múi giờ IANA, mặc định `Asia/Ho_Chi_Minh` |
| `ADMIN_EMAIL` | Có | Email admin bootstrap |
| `ADMIN_PASSWORD` | Có | Mật khẩu admin bootstrap mạnh |
| `ANTHROPIC_API_KEY` | Không | Trống thì AI dùng fallback |
| `ANTHROPIC_MODEL` | Khi dùng AI | Model Anthropic được account cho phép |
| `AI_ENABLED` | Không | Bật/tắt tính năng gọi AI |
| `REMINDER_WINDOW_MINUTES` | Không | Khoảng thời gian worker quét trước deadline |
| `VITE_API_URL` | Có cho frontend | Public API endpoint được nhúng lúc build |
| `VITE_WS_URL` | Có cho frontend | Public WebSocket endpoint được nhúng lúc build |

Production không được dùng credentials mẫu/hardcode. Hãy dùng secret manager của nền tảng triển khai.

## 8. API chính

| Method | Route | Chức năng |
|---|---|---|
| POST | `/api/v1/auth/register` | Tạo user và cấp token |
| POST | `/api/v1/auth/login` | Đăng nhập |
| POST | `/api/v1/auth/refresh` | Rotate refresh token |
| POST | `/api/v1/auth/logout` | Thu hồi refresh token |
| GET/PATCH | `/api/v1/auth/me` | Xem/sửa hồ sơ |
| GET/POST | `/api/v1/todos` | List/filter và tạo Todo |
| GET/PATCH/DELETE | `/api/v1/todos/{id}` | CRUD Todo thuộc user |
| GET | `/api/v1/todos/stats` | Thống kê Todo |
| GET/POST | `/api/v1/categories` | Danh mục của user |
| GET | `/api/v1/notifications` | Danh sách và unread count |
| PATCH/DELETE | `/api/v1/notifications/{id}/*` | Đọc/xóa notification |
| WS | `/api/v1/ws/notifications?token=...` | Realtime notification; cách truyền token này cần được harden |
| POST | `/api/v1/ai/suggest` | AI phân tích Todo |
| POST | `/api/v1/ai/chat` | Chat AI theo conversation |
| GET | `/api/v1/admin/users` | Admin xem user |
| PUT | `/api/v1/admin/users/{id}/roles` | Admin gán role |
| PATCH | `/api/v1/admin/users/{id}/active` | Admin khóa/mở user |

Swagger tại <http://localhost:8000/docs> là nguồn contract backend hiện tại. Frontend vẫn còn hai client method `/ai/suggestions` và `/ai/help` không có route backend tương ứng; xem phần lỗi đã biết.

## 9. Kiểm thử và kiểm tra chất lượng

Từ thư mục gốc:

```powershell
# Backend
.\backend\.venv\Scripts\python.exe -m pytest backend\tests -q
.\backend\.venv\Scripts\python.exe -m ruff check backend

# Frontend
npm --prefix frontend test
npm --prefix frontend run lint
npm --prefix frontend run build
npm --prefix frontend audit --omit=dev --audit-level=high

# Migration (cần DB đang chạy và env đúng)
cd backend
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m alembic check
```

Kết quả xác minh ngày **01/08/2026**:

| Kiểm tra | Kết quả |
|---|---|
| Backend pytest | 9 tests passed, gồm cookie/CSRF/refresh và DB-backed Todo/category/stats |
| Backend Ruff / compile | Passed |
| Frontend build | Passed |
| Frontend Vitest | 3 tests passed |
| Frontend ESLint | Passed, 0 warning |
| Docker health/readiness | API, web, PostgreSQL, Redis healthy; worker running |
| `alembic current` | `b93475648a93` là head hiện tại |
| `alembic check` | Passed, không còn model/migration drift |
| Local acceptance | Same-origin Nginx, cookie login, CSRF Todo create và WS ticket passed |
| Secret scan | Gitleaks passed |
| npm audit production deps | 2 high advisory qua React Router unstable RSC; SPA này không dùng RSC |

Test hiện đã chống regression cho auth cookie/CSRF/refresh/logout, validation, Todo/category/stats và WebSocket ticket. Các test chuyên sâu về multi-user RBAC, worker failure và AI provider vẫn thuộc backlog production.

## 10. Việc còn lại và lỗi đã biết

### Đã hoàn thành cho local

- [x] Production fail-fast cho default secret/admin/database và cookie settings.
- [x] Sửa migration drift bằng migration forward; `alembic check` xanh.
- [x] Nginx proxy same-origin `/api` và WebSocket; frontend không hardcode localhost API.
- [x] Access/refresh ở HttpOnly cookie, CSRF double-submit và WebSocket ticket dùng một lần.
- [x] Dashboard bỏ filter rỗng; `.env` resolve ổn định từ root.
- [x] Timezone-aware stats/display, validation đồng bộ và conflict trả `409`/`422`.
- [x] AI contract/reliability/history; category CRUD, stats/filter/sort/archive UI.
- [x] Error/loading/retry UX chính; worker commit trước publish; rate limit atomic và token retention.
- [x] Docker image production dependencies, non-root backend, `npm ci`, healthcheck và local acceptance smoke.

### Còn lại trước khi public production

- [ ] Rotate toàn bộ secret/credentials từng dùng trong `.env`; lưu bằng secret manager.
- [ ] Bật `COOKIE_SECURE=true`, HTTPS/WSS, domain thật và CORS production.
- [ ] Chạy database-clean migration/seed/login/CRUD/worker/WebSocket và backup/restore drill trên môi trường staging.
- [ ] Xử lý advisory React Router khi registry có bản vá tương thích. Advisory hiện chỉ ảnh hưởng unstable RSC API mà SPA không dùng; không chạy `npm audit fix --force` vì nó đề xuất downgrade breaking.
- [ ] Tăng test multi-user ownership/RBAC, worker failure/idempotency, WebSocket handshake và AI provider timeout/error.
- [ ] Thêm request ID, structured JSON logs, metrics, tracing/error monitoring và alert worker/readiness.
- [ ] Thêm resource limits, CI, backup automation và retention cho audit log/AI history; review privacy dữ liệu AI.
- [ ] Thay local `POSTGRES_PASSWORD=todo` và admin password hiện tại trước mọi hình thức public/deploy.

## 11. Xử lý lỗi thường gặp

### `no configuration file provided: not found`

Bạn đang đứng sai thư mục. Chạy:

```powershell
cd "D:\Dự án ma"
docker compose ps
```

### `ConnectionRefusedError: [WinError 1225]`

API không kết nối được PostgreSQL, Redis hoặc service khác:

```powershell
docker compose ps
docker compose logs --tail 100 postgres redis api worker
```

Quy tắc hostname:

- API chạy **trong Docker**: `postgres:5432`, `redis:6379`.
- API chạy **trực tiếp trên máy**: `localhost:5432`, `localhost:6379`.

### Port đã được sử dụng

Kiểm tra container đang giữ port 8000:

```powershell
docker ps --filter publish=8000 --format "table {{.ID}}`t{{.Names}}`t{{.Ports}}"
```

Kiểm tra process Windows:

```powershell
Get-NetTCPConnection -State Listen -LocalPort 8000,5432,6379,8080 -ErrorAction SilentlyContinue |
  Select-Object LocalAddress,LocalPort,OwningProcess
```

Dừng stack/container cũ hoặc đổi port publish trong `compose.yaml`; không dừng/xóa process khi chưa xác định nó thuộc ứng dụng nào.

### Dashboard không tải Todo và API trả `422`

Lỗi này đã được sửa: frontend loại filter rỗng trước khi gửi request. Nếu còn gặp `422`, mở Network tab để kiểm tra client cũ/cache và rebuild frontend.

### Chạy Alembic/Uvicorn trong `backend` nhưng dùng sai cấu hình

Backend luôn resolve `.env` từ root dự án. Khi chạy native, đặt `DATABASE_URL`/`REDIS_URL` qua biến môi trường hoặc root `.env`; không cần tạo `backend/.env` workaround nữa.

### `/ready` lỗi nhưng `/health` vẫn OK

`/health` chỉ kiểm tra process API; `/ready` kiểm tra cả PostgreSQL và Redis. Xem health và log hai dependency:

```powershell
docker compose ps
docker compose logs --tail 100 postgres redis api
```

### Không có notification realtime

1. Kiểm tra `worker` đang `Up`.
2. Kiểm tra `/ready`.
3. Xem `VITE_WS_URL`: local dùng `ws://`, production dùng `wss://`.
4. Reverse proxy production phải hỗ trợ `Upgrade`/`Connection` WebSocket.
5. Notification đã lưu vẫn có thể xuất hiện qua polling nếu WebSocket mất kết nối.

### AI luôn fallback

- `ANTHROPIC_API_KEY` đang trống/sai, model không được account cho phép hoặc `AI_ENABLED=false`.
- Restart API sau khi đổi env.
- Không ghi API key vào README, source hoặc log.

## 12. Cấu trúc chính

```text
.
├── compose.yaml              # Stack chính: PostgreSQL, Redis, API, worker, web
├── .env.example              # Template biến môi trường, không chứa secret thật
├── README.md                 # Cài đặt, setup, trạng thái và backlog
├── OPERATIONS_GUIDE.md       # Vận hành, backup/restore và production
├── backend/
│   ├── app/                  # FastAPI, models, schemas, services, worker
│   ├── alembic/              # Migration
│   ├── tests/                # Backend tests
│   ├── pyproject.toml        # Python dependencies/tooling
│   └── Dockerfile
└── frontend/
    ├── src/                  # React pages, API client, hooks, components
    ├── package.json
    ├── package-lock.json
    ├── nginx.conf
    └── Dockerfile
```

## 13. Production checklist tối thiểu

- [ ] Hoàn thành toàn bộ P0 và test lại từ database sạch.
- [ ] Secret, DB credentials và admin password mạnh, lưu trong secret manager.
- [ ] HTTPS/WSS qua reverse proxy; CORS chỉ cho domain thật.
- [ ] Không publish PostgreSQL/Redis ra Internet.
- [ ] Migration chạy như job một lần trước rollout; `alembic check` phải xanh.
- [ ] Backup PostgreSQL tự động và thử restore định kỳ.
- [ ] API/worker chạy non-root, không `--reload`, có restart/resource limits.
- [ ] Monitoring `/ready`, HTTP error/latency, DB pool, worker lag và disk.
- [ ] CI chạy backend/frontend tests, lint, build, migration và dependency audit.
- [ ] Review privacy/retention trước khi gửi nội dung Todo/chat cho AI provider.

Xem thêm quy trình backup, restore, migration và vận hành tại [OPERATIONS_GUIDE.md](OPERATIONS_GUIDE.md).
