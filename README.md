# Dohub (DeepOps)

Nền tảng hub quản lý và spawn workspace **code-server** (và container tùy chỉnh) trên Kubernetes, với đăng nhập GitHub và giao diện web.

![Dohub](./docs/assets/logo.png)

## Tài liệu

**Wiki đầy đủ (GitHub Pages):** [https://daovietanh190499.github.io/DeepOps/](https://daovietanh190499.github.io/DeepOps/)

Bao gồm: cài đặt cluster, hướng dẫn user/admin từng tính năng, Keycloak và Overleaf.

Tài liệu nguồn nằm trong thư mục [`docs/`](./docs/). Sau khi sửa nội dung:

```bash
cd docs
python3 scripts/make_placeholder.py   # tùy chọn — placeholder ảnh
python3 build.py                    # generate HTML wiki
```

Chụp ảnh màn hình thật (cần Playwright + Chromium):

```bash
cd docs
python3 -m pip install playwright
python3 -m playwright install chromium
export DOHUB_URL=https://iaihub.uet.edu.vn
python3 scripts/capture_screenshots.py
```

## Highlights

- Code trên trình duyệt với môi trường thống nhất
- Spawn workspace theo CPU / RAM / GPU qua Helm (`charts/codehub`)
- DirectPV drives, monitor, backup rclone, wstunnel expose port
- Quản trị cluster, user, template từ trang Admin

## Kiến trúc

| Thành phần | Đường dẫn |
|------------|-----------|
| Backend Django | `DeepOpsBackend/` |
| Chart hub | `dohub/` |
| Chart workspace | `charts/codehub/` |
| Chart Jenkins (tuỳ chọn) | `charts/jenkins/` |

## Triển khai nhanh

Chi tiết: [Cài đặt cluster](https://daovietanh190499.github.io/DeepOps/installation.html) hoặc [`DEPLOY.md`](./DEPLOY.md).

```bash
cp dohub/secrets/.env.example dohub/secrets/.env
# chỉnh .env và dohub/configmap/config.yaml

chmod +x build-and-deploy.sh
./build-and-deploy.sh all
```

## Production

- Hub: [https://iaihub.uet.edu.vn](https://iaihub.uet.edu.vn)
- Keycloak: [https://keycloak.iaihub.uet.edu.vn](https://keycloak.iaihub.uet.edu.vn)
- Overleaf: [https://overleaf.iaihub.uet.edu.vn](https://overleaf.iaihub.uet.edu.vn)

## Requirements

- Linux, ingress nginx, WebSockets
- Kubernetes + Helm 3 + DirectPV (`directpv-min-io`)
- ~1 GB RAM cho hub pod (khuyến nghị)
