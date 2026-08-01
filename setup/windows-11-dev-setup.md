# Setup môi trường lập trình Windows 11

> Cập nhật kiểm tra: **2026-08-01**
> Mô hình khuyên dùng: **Windows 11 + Docker Desktop + WSL2 Ubuntu + VS Code Remote WSL**.

---

## 1. Trạng thái máy hiện tại

### Đã cài và hoạt động

| Thành phần | Trạng thái |
|---|---|
| Docker Desktop | `4.84.0`, đang chạy |
| Docker Engine | `29.6.2`, Linux/AMD64, hoạt động |
| Docker Compose | `v5.3.1` |
| Docker context | `desktop-linux` |
| WSL | `2.7.11.0`, WSL2 hoạt động |
| WSL kernel | `6.18.33.2-microsoft-standard-WSL2` |
| Git | `2.55.0.windows.3` |
| Python | `3.14.6` |
| Node.js | `v24.16.0` |
| npm | `11.13.0` |
| VS Code | `1.131.0` |
| WinGet | `v1.29.280` |

### Docker đã được xác minh

```text
Docker Desktop: running
Client: 29.6.2 / windows-amd64
Server: 29.6.2 / linux-amd64
Context: desktop-linux
Kernel: 6.18.33.2-microsoft-standard-WSL2
CPU cấp cho Docker: 12
RAM cấp cho Docker: khoảng 8 GB
```

Smoke test đã chạy thành công:

```powershell
docker run --rm hello-world
```

Kết quả: Docker client kết nối được daemon, pull image và chạy container thành công.

### Còn thiếu hoặc chưa cấu hình

- Chưa có Ubuntu dành cho development; WSL hiện chỉ có distro nội bộ `docker-desktop`.
- Chưa cài PowerShell 7 (`pwsh`).
- Chưa cài GitHub CLI (`gh`).
- Chưa cài `uv` để quản lý Python/project.
- Chưa cài Bruno và DBeaver.
- Git global chưa có `user.name`, `user.email`, default branch và line-ending policy.
- Python launcher `py -0p` gặp lỗi encoding vì đường dẫn hiện tại chứa ký tự tiếng Việt.
- Terminal hiện đang kế thừa virtualenv:

```text
D:\Dự án ma\backend\.venv
```

---

## 2. Kết luận lỗi Docker đã gặp

Lỗi ban đầu:

```text
failed to connect to the docker API at
npipe:////./pipe/dockerDesktopLinuxEngine
The system cannot find the file specified.
```

### Nguyên nhân

Docker CLI đã chọn đúng context `desktop-linux`, nhưng tại thời điểm chạy lệnh, Linux engine của Docker Desktop chưa khởi động xong. Vì vậy named pipe sau chưa tồn tại:

```text
//./pipe/dockerDesktopLinuxEngine
```

Đây không phải lỗi version hoặc sai context. Sau khi Docker Desktop khởi động hoàn tất, client và daemon đã kết nối bình thường.

### Nếu lỗi tái diễn

Chạy trong PowerShell:

```powershell
docker desktop status
```

Nếu chưa chạy:

```powershell
docker desktop start
```

Chờ đến khi:

```powershell
docker desktop status
docker version
```

`docker version` phải hiện đủ cả hai phần:

```text
Client:
Server:
```

Nếu Docker Desktop báo `running` nhưng vẫn không có `Server`:

```powershell
docker desktop restart
```

Sau đó kiểm tra:

```powershell
docker context use desktop-linux
docker version
docker info
docker run --rm hello-world
```

Nếu vẫn lỗi, cập nhật và restart WSL:

> Cảnh báo: `wsl --shutdown` sẽ dừng toàn bộ tiến trình/container đang chạy trong WSL, nhưng không xóa volume.

```powershell
wsl --update
wsl --shutdown
```

Mở lại Docker Desktop, đợi engine sẵn sàng rồi chạy:

```powershell
docker version
docker run --rm hello-world
```

Không bật tùy chọn Docker daemon TCP không TLS và không cài lại Docker khi chưa thử các bước trên.

---

## 3. Cài bộ công cụ Windows còn thiếu

Mở **PowerShell bằng quyền Administrator**:

```powershell
winget install -e --id Microsoft.WindowsTerminal
winget install -e --id Microsoft.PowerShell
winget install -e --id Microsoft.VisualStudioCode
winget install -e --id 7zip.7zip
winget install -e --id Microsoft.PowerToys
winget install -e --id Bruno.Bruno
winget install -e --id DBeaver.DBeaver.Community
```

Công dụng:

- **PowerShell 7**: shell hiện đại cho Windows.
- **VS Code**: editor chính.
- **Bruno**: test API, collection có thể lưu trong Git.
- **DBeaver**: quản lý PostgreSQL/MySQL.
- **PowerToys** và **7-Zip**: tiện ích, không bắt buộc.

Kiểm tra:

```powershell
pwsh --version
code --version
winget list -e --id Bruno.Bruno
winget list -e --id DBeaver.DBeaver.Community
```

---

## 4. Cài Ubuntu 24.04 trên WSL2

Docker Desktop dùng WSL2 nhưng distro `docker-desktop` không phải môi trường để viết code. Cài Ubuntu riêng:

```powershell
wsl --list --online
wsl --install -d Ubuntu-24.04
```

Restart Windows nếu được yêu cầu, sau đó:

```powershell
wsl --update
wsl --set-default-version 2
wsl --set-default Ubuntu-24.04
wsl --list --verbose
```

Kết quả cần có dạng:

```text
NAME              STATE      VERSION
Ubuntu-24.04      Running    2
docker-desktop    Running    2
```

Lần đầu mở Ubuntu:

- Tạo username Linux.
- Tạo password Linux.
- Khi nhập password không hiện ký tự là bình thường.

Trong Ubuntu, cài package nền:

```bash
sudo apt update
sudo apt full-upgrade -y
sudo apt install -y \
  build-essential \
  ca-certificates \
  curl \
  git \
  gh \
  jq \
  make \
  openssh-client \
  unzip \
  zip
```

Tạo nơi chứa source:

```bash
mkdir -p ~/code
cd ~/code
```

Nên đặt project ở:

```text
/home/<username>/code
```

Tránh đặt source dùng Docker/Python trong:

```text
/mnt/c/Users/...
/mnt/d/Dự án có dấu/...
OneDrive/...
```

Đường dẫn có dấu/khoảng trắng dễ gây lỗi encoding, script và tooling. Máy hiện đã gặp lỗi `py -0p` liên quan đường dẫn `D:\Dự án ma`.

---

## 5. Kết nối Ubuntu với Docker Desktop

Trong Docker Desktop:

1. Mở **Settings → General**.
2. Bật **Use the WSL 2 based engine**.
3. Mở **Settings → Resources → WSL Integration**.
4. Bật integration cho `Ubuntu-24.04`.
5. Chọn **Apply & restart**.

Trong Ubuntu kiểm tra:

```bash
docker version
docker compose version
docker run --rm hello-world
```

Không cài package `docker-compose` bản cũ. Docker Desktop đã cung cấp Compose V2 qua lệnh:

```bash
docker compose
```

---

## 6. Cấu hình Git trong Ubuntu

Thay tên/email bằng thông tin thật:

```bash
git config --global user.name "TEN_GITHUB"
git config --global user.email "EMAIL_GITHUB"
git config --global init.defaultBranch main
git config --global core.autocrlf input
git config --global core.eol lf
git config --global fetch.prune true
git config --global core.editor "code --wait"
```

Kiểm tra:

```bash
git config --global --list
```

Không cấu hình:

```bash
git config --global safe.directory '*'
```

Lệnh đó vô hiệu hóa một lớp kiểm tra bảo mật của Git.

### Tạo SSH key

```bash
ssh-keygen -t ed25519 -C "EMAIL_GITHUB"
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
clip.exe < ~/.ssh/id_ed25519.pub
```

Thêm public key vào:

```text
GitHub → Settings → SSH and GPG keys → New SSH key
```

Kiểm tra:

```bash
ssh -T git@github.com
```

Hoặc đăng nhập bằng GitHub CLI:

```bash
gh auth login --web --git-protocol ssh
```

Chỉ chia sẻ file `id_ed25519.pub`. Không gửi hoặc commit private key `id_ed25519`.

---

## 7. Setup VS Code cho WSL

Chạy trong PowerShell:

```powershell
code --install-extension ms-vscode-remote.remote-wsl
code --install-extension ms-python.python
code --install-extension ms-python.vscode-pylance
code --install-extension charliermarsh.ruff
code --install-extension ms-azuretools.vscode-docker
code --install-extension ms-vscode-remote.remote-containers
code --install-extension redhat.vscode-yaml
code --install-extension EditorConfig.EditorConfig
```

Mở project từ Ubuntu:

```bash
cd ~/code
code .
```

Góc trái dưới VS Code cần hiển thị:

```text
WSL: Ubuntu-24.04
```

VS Code settings đề xuất:

```json
{
  "files.eol": "\n",
  "editor.formatOnSave": true,
  "python.analysis.typeCheckingMode": "basic",
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.codeActionsOnSave": {
      "source.fixAll.ruff": "explicit",
      "source.organizeImports.ruff": "explicit"
    }
  }
}
```

---

## 8. Setup Python bằng `uv`

Cài trong Ubuntu:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
exec bash
uv --version
```

Nếu muốn xem script trước khi chạy:

```bash
curl -LsSf https://astral.sh/uv/install.sh -o /tmp/uv-install.sh
less /tmp/uv-install.sh
sh /tmp/uv-install.sh
```

Cài Python ổn định cho project:

```bash
uv python install 3.13
uv python list
```

Python Windows hiện là `3.14.6`, nhưng với backend nên pin Python theo compatibility của dependencies. Python 3.13 thường an toàn hơn cho project mới tại thời điểm ghi chú này.

### Tạo FastAPI project mẫu

```bash
mkdir -p ~/code/hello-api
cd ~/code/hello-api
uv init --python 3.13
uv add "fastapi[standard]" pydantic-settings
uv add --dev ruff pytest pytest-asyncio httpx mypy
mkdir -p app
```

Tạo `app/main.py`:

```python
from fastapi import FastAPI

app = FastAPI(title="Hello API")


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
```

Chạy:

```bash
uv run fastapi dev app/main.py
```

Mở:

```text
http://127.0.0.1:8000/health
http://127.0.0.1:8000/docs
```

Kiểm tra code:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

Không cần activate `.venv` thủ công khi dùng `uv run`.

---

## 9. PostgreSQL và Redis bằng Docker

Không cần cài PostgreSQL/Redis trực tiếp lên Windows.

```bash
mkdir -p ~/code/dev-infra
cd ~/code/dev-infra
```

Tạo `.env`:

```dotenv
POSTGRES_DB=app
POSTGRES_USER=app
POSTGRES_PASSWORD=change-this-dev-password
```

Tạo `compose.yaml`:

```yaml
services:
  postgres:
    image: postgres:17-alpine
    restart: unless-stopped
    env_file:
      - .env
    ports:
      - "127.0.0.1:5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB"]
      interval: 5s
      timeout: 3s
      retries: 10

  redis:
    image: redis:7.4-alpine
    restart: unless-stopped
    command: ["redis-server", "--appendonly", "yes"]
    ports:
      - "127.0.0.1:6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10

volumes:
  postgres_data:
  redis_data:
```

Chạy:

```bash
docker compose up -d
docker compose ps
docker compose logs -f
```

Dừng và giữ dữ liệu:

```bash
docker compose down
```

> Cảnh báo: lệnh dưới đây xóa luôn dữ liệu PostgreSQL/Redis trong volume.

```bash
docker compose down -v
```

DBeaver connection:

```text
Host: localhost
Port: 5432
Database: app
Username: app
Password: giá trị POSTGRES_PASSWORD
```

Thêm vào `.gitignore`:

```gitignore
.env
.venv/
__pycache__/
.pytest_cache/
.ruff_cache/
.mypy_cache/
```

Commit `.env.example`, không commit `.env` hoặc secret thật.

---

## 10. Node.js

Máy đã có:

```text
Node.js v24.16.0
npm 11.13.0
```

Khi chuyển development sang WSL, nên cài Node riêng trong Ubuntu bằng `fnm`, không trộn Node/npm Windows với project WSL:

```bash
curl -fsSL https://fnm.vercel.app/install | bash
source ~/.bashrc
fnm install --lts
fnm default lts-latest
node --version
npm --version
which node
which npm
```

`which node` và `which npm` phải trả về đường dẫn Linux do FNM quản lý. Đường dẫn hiện hành thường có dạng `/run/user/<uid>/fnm_multishells/...`; đây là bình thường. Mục đầu tiên không được là `/mnt/c/...`.

Nếu dùng pnpm, bật bản do Node cung cấp qua Corepack:

```bash
corepack enable
corepack prepare pnpm@latest --activate
hash -r
pnpm --version
which pnpm
```

Nếu trước đó đã vô tình cài `pnpm` bằng npm Windows từ WSL và `which pnpm` trỏ vào `/mnt/c/Users/...`, không dùng binary đó. Sau khi `fnm install --lts` hoàn tất, các lệnh Corepack phía trên sẽ đặt `pnpm` trong môi trường Node của WSL.

---

## 11. Giới hạn RAM cho WSL khi cần

Docker hiện được cấp khoảng **8 GB RAM** và **12 CPU**. Nếu máy chạy ổn thì không cần chỉnh.

Nếu cần giới hạn, mở trong PowerShell:

```powershell
notepad $env:USERPROFILE\.wslconfig
```

Ví dụ cho máy có 16 GB RAM:

```ini
[wsl2]
memory=8GB
processors=4
swap=2GB

[experimental]
autoMemoryReclaim=gradual
```

Áp dụng:

```powershell
wsl --shutdown
```

Lệnh này dừng toàn bộ tiến trình/container WSL đang chạy nhưng không xóa volume.

---

## 12. Checklist hoàn tất

### PowerShell

```powershell
wsl --list --verbose
docker desktop status
docker version
docker compose version
git --version
py -0p
code --version
pwsh --version
```

### Ubuntu

```bash
git --version
gh --version
uv --version
uv python list
docker version
docker compose version
docker run --rm hello-world
```

### Trạng thái chuẩn — kiểm tra thực tế ngày 2026-08-01

- [x] Docker Desktop chạy bằng Linux engine.
- [x] Docker client kết nối được Docker daemon.
- [x] `hello-world` chạy thành công từ Windows và Ubuntu.
- [x] Docker Compose hoạt động (`v5.3.1`).
- [x] WSL2 hoạt động, Ubuntu 24.04 là distro mặc định.
- [x] Ubuntu 24.04 đã được cài riêng cho development.
- [x] Thư mục source `~/code` đã tồn tại trong Ubuntu.
- [x] Git đã có name/email, default branch và line-ending policy.
- [x] SSH key GitHub đã được tạo và đã từng xác thực thành công.
- [x] Python 3.13 được quản lý bằng `uv`.
- [x] Node.js/npm/pnpm được quản lý trong WSL bằng FNM/Corepack.
- [x] Bruno, DBeaver, PowerShell 7, Windows Terminal, 7-Zip và PowerToys đã được cài.
- [x] Đủ các VS Code extension được đề xuất ở phía Windows.
- [x] Đã tạo `~/.ssh/config` để GitHub luôn chọn key mới và `.bashrc` dùng chung một SSH agent giữa các shell; terminal mới sẽ hỏi passphrase một lần để nạp key.
- [x] Đăng nhập GitHub CLI thành công với tài khoản `devilc312`; Git operations dùng SSH.
- [x] Đã áp dụng VS Code settings: LF, format-on-save, Python type checking `basic` và Ruff formatter/fix imports khi lưu.
- [x] Đã mở `~/code` bằng VS Code và xác minh WSL daemon/server đang chạy trên `Ubuntu-24.04`; extensions Python, Pylance, Ruff, Docker và YAML đã cài phía WSL.
- [x] Đã tạo `~/code/dev-infra` cho PostgreSQL 17/Redis 7.4, smoke-test `healthy` + `SELECT 1`/`PING`, rồi dừng container và giữ named volumes. Chỉ `docker compose up -d` khi project cần.
- [x] Đã tạo `~/code/hello-api` bằng uv/Python 3.13; Ruff pass và Pytest `1 passed`.
- [x] Đã cài Gitleaks 8.30.1 trên Windows/WSL; project hiện tại, history của `hello-api` và working tree `dev-infra` đều scan pass. Dùng `~/code/scan-git-secrets.sh` để scan lại toàn bộ repository trong `~/code`.

---

## 13. Các lệnh Docker hay dùng

```powershell
# Trạng thái Docker Desktop
docker desktop status

# Kiểm tra client/server
docker version

# Thông tin engine
docker info

# Danh sách context
docker context ls

# Chọn Linux engine của Docker Desktop
docker context use desktop-linux

# Danh sách container
docker ps -a

# Danh sách image
docker images

# Dung lượng Docker đang dùng
docker system df
```

Không chạy tùy tiện:

```powershell
docker system prune -a --volumes
```

Lệnh trên có thể xóa image, cache, container và volume không sử dụng, dẫn đến mất dữ liệu local.
