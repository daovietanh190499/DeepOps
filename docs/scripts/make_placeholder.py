#!/usr/bin/env python3
"""Create SVG placeholder images for documentation screenshots."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets' / 'screenshots'
OUT.mkdir(parents=True, exist_ok=True)

SHOTS = [
    ('login', 'Đăng nhập GitHub'),
    ('drives-list', 'Tab My drives'),
    ('drives-create-modal', 'Modal Create drive'),
    ('drives-delete-modal', 'Modal Delete drive'),
    ('servers-list', 'Tab My servers'),
    ('servers-create-modal', 'Modal Create server'),
    ('servers-form-fields', 'Các trường cấu hình server'),
    ('servers-edit-modal', 'Modal Edit server'),
    ('servers-start-stop', 'Nút Start / Stop'),
    ('servers-delete-modal', 'Modal Delete server'),
    ('images-submit', 'Đăng ký Docker image'),
    ('images-pending', 'Trạng thái pending'),
    ('port-expose', 'Expose port wstunnel'),
    ('logs-tab', 'Tab Logs'),
    ('describe-tab', 'Tab Describe'),
    ('terminal-tab', 'Tab Terminal'),
    ('monitor-tab', 'Tab Monitor'),
    ('backup-tab', 'Tab Backup'),
    ('custom-domain', 'Service domain'),
    ('admin-overall', 'Admin Cluster overall'),
    ('admin-directpv-discover', 'DirectPV discover'),
    ('admin-directpv-init', 'DirectPV init confirm'),
    ('admin-drives', 'Admin Drives'),
    ('admin-servers', 'Admin Servers'),
    ('admin-templates', 'Quick templates'),
    ('admin-users', 'Admin Users'),
    ('admin-accept-user', 'Accept user'),
    ('admin-groups', 'Resource groups'),
    ('admin-group-form', 'Create group'),
    ('admin-images', 'Admin Docker images'),
    ('admin-accept-image', 'Accept image'),
    ('keycloak-login', 'Keycloak đăng nhập'),
    ('keycloak-realm', 'Tạo realm'),
    ('keycloak-client', 'Tạo client'),
    ('keycloak-groups', 'Groups Keycloak'),
    ('overleaf-login', 'Overleaf đăng nhập'),
    ('overleaf-wait-group', 'Chờ admin add group'),
    ('overleaf-admin-group', 'Admin add user vào group'),
]


def svg(name: str, caption: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
  <rect width="1280" height="720" fill="#f8fafc"/>
  <rect x="40" y="40" width="1200" height="640" rx="16" fill="#0f172a" opacity="0.04" stroke="#cbd5e1"/>
  <text x="640" y="300" text-anchor="middle" font-family="system-ui,sans-serif" font-size="42" font-weight="700" fill="#0f172a">Dohub Docs</text>
  <text x="640" y="360" text-anchor="middle" font-family="system-ui,sans-serif" font-size="22" fill="#64748b">{caption}</text>
  <text x="640" y="420" text-anchor="middle" font-family="ui-monospace,monospace" font-size="16" fill="#94a3b8">{name}.png — chạy scripts/capture_screenshots.py để thay ảnh thật</text>
</svg>'''


def main() -> None:
    for name, caption in SHOTS:
        path = OUT / f'{name}.svg'
        path.write_text(svg(name, caption), encoding='utf-8')
        print('wrote', path.name)


if __name__ == '__main__':
    main()
