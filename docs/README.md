# Dohub Documentation Wiki

Static documentation site for [Dohub](https://iaihub.uet.edu.vn), published via GitHub Pages:

**https://daovietanh190499.github.io/DeepOps/**

## Cấu trúc

```
docs/
  build.py              # Generator HTML từ content fragments
  index.html            # (generated) Trang chủ wiki
  installation.html     # (generated) Cài đặt cluster
  user/                 # (generated) Hướng dẫn người dùng
  admin/                # (generated) Hướng dẫn admin
  apps/                 # (generated) Keycloak, Overleaf
  content/              # Nguồn nội dung (.html + .json metadata)
  assets/
    logo.png            # Logo Dohub
    screenshots/        # Ảnh minh họa (.svg placeholder hoặc .png thật)
  scripts/
    make_placeholder.py
    capture_screenshots.py
```

Theme dựa trên [Spinal docs template](https://github.com/spinalcms/docs-template) (Tailwind CSS + typography), đã rebrand cho Dohub.

## Build

```bash
cd docs
python3 build.py
```

Sửa nội dung trong `content/*.html` và `content/*.json`, rồi chạy lại `build.py`.

## Ảnh minh họa

Placeholder SVG được tạo bằng:

```bash
python3 scripts/make_placeholder.py
```

Thay bằng screenshot PNG cùng tên (bỏ `.svg`, dùng `.png`) và cập nhật thẻ `<img>` trong content nếu cần.

Script chụp ảnh (Playwright):

```bash
# Một lần: cài thư viện Chromium (không cần sudo)
bash scripts/setup_chromium_libs.sh

# Tạo .env.capture từ .env.capture.example
cp .env.capture.example .env.capture
# Điền DOCS_USER_TOKEN / DOCS_ADMIN_TOKEN (GitHub PAT) — khuyến nghị, tránh OTP

# Chạy
bash scripts/run_capture.sh
```

**Đăng nhập bằng cookie Dohub (khuyến nghị):** lấy `user_access_key` từ DevTools → Application → Cookies → `iaihub.uet.edu.vn`:

```bash
DOCS_USER_COOKIE=uuid-của-daovietanh99
DOCS_ADMIN_COOKIE=uuid-của-agentdv
```

Cookie hết hạn khi đăng nhập lại trên trình duyệt — cần lấy giá trị mới.

**Đăng nhập GitHub** (nếu không có cookie): mật khẩu/PAT → OTP hỏi sau khi email tới.

Session lưu tại `docs/.auth/` sau lần chạy thành công.

**Quy tắc:** chỉ tạo/xóa tài nguyên demo (`docs-demo-*`). **Không** chạy DirectPV discover/init khi chụp ảnh.

## Tailwind (tuỳ chọn)

Nếu có Node.js:

```bash
npm install
npx tailwindcss -i ./src/input.css -o ./dist/output.css --minify
```

Trang generated hiện dùng Tailwind CDN; `dist/output.css` là tùy chọn cho offline build.
