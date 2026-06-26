# Dohub Documentation Wiki

Static documentation site for Dohub, published via GitHub Pages:

**https://daovietanh190499.github.io/DeepOps/docs/**

Hỗ trợ song ngữ **Tiếng Việt / English** — dùng nút cờ 🇻🇳 / 🇬🇧 trên header.

## Cấu trúc

```
docs/
  build.py              # Generator HTML (bilingual VI/EN)
  locales/              # Chuỗi UI + navigation
  content/
    vi/                 # Nội dung tiếng Việt (.html + .json)
    en/                 # Nội dung tiếng Anh
  assets/
    docs.css, docs.js   # Style code blocks + language switcher
    logo.png
    screenshots/        # Ảnh minh họa (.png)
  scripts/
    capture_screenshots.py
    migrate_i18n.py
```

## Build

```bash
cd docs
python3 build.py
```

Sửa nội dung trong `content/vi/` (và `content/en/` nếu cần), rồi chạy lại `build.py`.

## Ảnh minh họa

Script chụp ảnh (Playwright):

```bash
# Một lần: cài thư viện Chromium (không cần sudo)
bash scripts/setup_chromium_libs.sh

# Tạo .env.capture từ .env.capture.example
cp .env.capture.example .env.capture
# Điền DOHUB_URL (hub của bạn) và DOCS_USER_COOKIE / DOCS_ADMIN_COOKIE

bash scripts/run_capture.sh
```

**Đăng nhập bằng cookie Dohub (khuyến nghị):** lấy `user_access_key` từ DevTools → Application → Cookies → domain hub của bạn:

```bash
DOCS_USER_COOKIE=uuid-user
DOCS_ADMIN_COOKIE=uuid-admin
```

Cookie hết hạn khi đăng nhập lại trên trình duyệt — cần lấy giá trị mới.

**Quy tắc:** chỉ tạo/xóa tài nguyên demo (`docs-demo-*`). **Không** chạy DirectPV discover/init khi chụp ảnh.
