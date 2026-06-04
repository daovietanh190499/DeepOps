# Triển khai DeepOps (Django + Helm)

## Cấu trúc repo

| Thư mục | Mô tả |
|---------|--------|
| `DeepOpsBackend/` | Backend Django (hub, API, templates, static) |
| `charts/codehub/` | Helm chart spawn code-server cho từng user |
| `dohub/` | Helm chart deploy toàn bộ hệ thống (hub + ingress + DirectPV) |

## Yêu cầu

- Docker
- Kubernetes cluster + `kubectl`
- Helm 3
- NGINX Ingress Controller
- [DirectPV](https://github.com/minio/directpv) với StorageClass `directpv-min-io` (`WaitForFirstConsumer`)

## 1. Cấu hình

```bash
cp dohub/secrets/.env.example dohub/secrets/.env
# Sửa GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, ADMIN_USERS, DOMAIN_NAME, ...
```

Chỉnh `storage` và `volumeSize` theo gói server trong `dohub/configmap/config.yaml`.

Chỉnh host ingress trong `dohub/values.yaml` (`ingress.hosts`, TLS).

## 2. Build & deploy (`build-and-deploy.sh`)

```bash
chmod +x build-and-deploy.sh
./build-and-deploy.sh --help
```

Chỉ build:

```bash
./build-and-deploy.sh build
```

Build + push + tag tùy chỉnh:

```bash
./build-and-deploy.sh -r your-registry/dohub -t 1.0.0 -p build
```

Chỉ deploy:

```bash
./build-and-deploy.sh -n dohub --release dohub deploy
```

Build + deploy + file values riêng:

```bash
./build-and-deploy.sh -r your-registry/dohub -t 1.0.0 -f dohub/values-prod.yaml all
```

Tham số thường dùng: `-r` repo, `-t` tag, `-n` namespace, `--release`, `-p` push, `-f` values, `--no-restart`.

Deploy thủ công:

```bash
helm upgrade --install dohub ./dohub \
  --create-namespace -n dohub \
  --reset-values \
  --set image.repository=daovietanh99/dohub \
  --set image.tag=latest
```

## 4. GitHub OAuth callback

Đăng ký OAuth App với callback URL:

`https://<ingress-host>/github-callback`

## 5. Truy cập user workspace

Sau khi user **Start Server**, code-server được cài qua chart `charts/codehub` tại:

`https://<username>.<DOMAIN_NAME>/`

(`DOMAIN_NAME` trong `.env` / ConfigMap.)

## 6. Phát triển local

```bash
cd DeepOpsBackend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export CONFIG_PATH=config/config.yaml
export DATABASE_HOST=db.sqlite3
python manage.py migrate
python manage.py runserver 0.0.0.0:5000
```

Mở http://localhost:5000

## Drives (DirectPV) vs servers

- **Drives** tab: user creates a DirectPV PVC (`kubectl apply`) with name + size (`20Gi`, …).
- **Servers** no longer create storage; pick an existing drive + **mount path** (e.g. `/home/coder`).
- PVC name: `drive-{namespace}-{username}-{slug}`.
- Delete drive: type `delete` in modal; blocked if a server still uses it or server is running.

API: `GET/POST /drives/create`, `DELETE /drives/<id>`, `GET /admin/drives`.

## Workspaces (multi-server)

- **Home**: cấu hình CPU/RAM/GPU/Drive, docker image+tag, ENV, ports, command → **Run codehub**
- **My servers**: quản lý nhiều server / user
- **Admin → Users**: chỉ accept/role/delete (không bật tắt server)
- **Admin → Servers**: lưới card, lọc user, phân trang
- **Admin → Images**: danh sách docker image cho user chọn
- Template Lollipop/Oreo/… chỉ fill form trên UI (không còn plan trong DB)
- Hostname mỗi server: `{slug}.{username}.{DOMAIN_NAME}`

API chính: `POST /workspaces/run`, `GET /workspaces`, `POST /workspaces/<id>/start|stop`, `GET /workspaces/<id>/export`

## Code-server behind nginx ingress (WebSocket / session)

Each codehub release sets ingress annotations for WebSocket upgrade and proxy headers (`Host`, `Upgrade`, `Connection`, `X-Forwarded-*`). Custom `codehub` images may not support the code-server `--trust-proxy` CLI flag; proxy trust is handled via ingress headers only.

After chart changes, **Stop → Start** each workspace (or `helm upgrade` the release) so ingress picks up new annotations.

If your cluster blocks `configuration-snippet`, allow it on the nginx ingress controller or add equivalent headers in your ingress controller config.

## Codehub login / PASSWORD

code-server (and most `codehub` images) read **`PASSWORD`** from a Kubernetes Secret (`env.secret.PASSWORD`), not only plain env. The hub maps your workspace ENV `PASSWORD` into that secret on spawn.

If login always fails after you changed the password:

1. **Stale PVC** — an old `/home/coder/.config/code-server/config.yaml` keeps the previous hash. Re-**Start** the server from the hub (deploy sets `auth.resetConfigOnDeploy=true` when `PASSWORD` is set), or delete the workspace PVC and start again.
2. **Confirm ENV** — in Home / workspace modal, ensure `PASSWORD` is listed under environment variables before run.
3. **Redeploy hub** after chart changes: `./build-and-deploy.sh -t latest all`

## Debug spawn codehub

```bash
./test-codehub.sh preflight
USERNAME=your_github_user PASSWORD=your_code_password ./test-codehub.sh spawn
USERNAME=your_github_user ./test-codehub.sh status
# Test từ trong pod hub (giống UI Start):
FROM_HUB_POD=1 USERNAME=... PASSWORD=... ./test-codehub.sh hub-exec
```
