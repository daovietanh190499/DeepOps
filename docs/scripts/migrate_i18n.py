#!/usr/bin/env python3
"""One-time helper: bilingual JSON meta + English HTML copies."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VI = ROOT / 'content' / 'vi'
EN = ROOT / 'content' / 'en'

DOMAIN_MAP = [
    (r'https?://iaihub\.uet\.edu\.vn/?', 'https://hub.example.com/'),
    (r'iaihub\.uet\.edu\.vn', 'hub.example.com'),
    (r'https?://keycloak\.iaihub\.uet\.edu\.vn/?', 'https://keycloak.example.com/'),
    (r'keycloak\.iaihub\.uet\.edu\.vn', 'keycloak.example.com'),
    (r'https?://overleaf\.iaihub\.uet\.edu\.vn/?', 'https://overleaf.example.com/'),
    (r'overleaf\.iaihub\.uet\.edu\.vn', 'overleaf.example.com'),
]

EN_SECTION = {
    'Bắt đầu': 'Getting started',
    'Người dùng': 'User guide',
    'Quản trị viên': 'Administrator',
    'Ứng dụng trên Dohub': 'Apps on Dohub',
}

EN_META: dict[str, dict] = {
    'installation.json': {
        'title': 'Cluster installation',
        'subtitle': 'Deploy MicroK8s, DirectPV, HAMi, and Dohub from scratch.',
    },
    'user-drives.json': {
        'title': 'Create & delete drives',
        'subtitle': 'Manage DirectPV volumes attached to workspaces.',
    },
    'user-servers.json': {
        'title': 'Manage servers',
        'subtitle': 'Create, edit, start, stop, and delete code-server workspaces.',
    },
    'user-images.json': {
        'title': 'Register Docker images',
        'subtitle': 'Submit custom images and wait for admin approval.',
    },
    'user-port-expose.json': {
        'title': 'Expose port (wstunnel)',
        'subtitle': 'Forward TCP ports through the hub wstunnel proxy.',
    },
    'user-logs-describe.json': {
        'title': 'Logs & Describe',
        'subtitle': 'Inspect pod logs and Kubernetes object descriptions.',
    },
    'user-terminal.json': {
        'title': 'Interactive terminal',
        'subtitle': 'Shell into the main workspace container from the browser.',
    },
    'user-monitor.json': {
        'title': 'Resource monitor',
        'subtitle': 'CPU, memory, and GPU usage for a running server.',
    },
    'user-backup.json': {
        'title': 'Rclone backup',
        'subtitle': 'Backup workspace data to remote storage.',
    },
    'user-custom-domain.json': {
        'title': 'Custom domain',
        'subtitle': 'Custom ingress hostname for workspaces (group permission).',
    },
    'admin-overall.json': {
        'title': 'Cluster overall',
        'subtitle': 'Cluster info, join nodes, SSH, and DirectPV drive list.',
    },
    'admin-directpv.json': {
        'title': 'DirectPV discover & init',
        'subtitle': 'Discover raw drives and initialize DirectPV (destructive).',
    },
    'admin-drives.json': {
        'title': 'Manage drives',
        'subtitle': 'View and delete all user drives (admin).',
    },
    'admin-servers.json': {
        'title': 'Manage servers',
        'subtitle': 'View all workspaces across users.',
    },
    'admin-templates.json': {
        'title': 'Server templates',
        'subtitle': 'Catalog of spawn templates (CPU, RAM, image, mounts).',
    },
    'admin-users.json': {
        'title': 'Users & accept',
        'subtitle': 'Pending users, roles, and acceptance.',
    },
    'admin-groups.json': {
        'title': 'Resource groups',
        'subtitle': 'Quotas, permissions, and group membership.',
    },
    'admin-docker-images.json': {
        'title': 'Docker images',
        'subtitle': 'Approve or reject user-submitted images.',
    },
    'apps-keycloak.json': {
        'title': 'Keycloak (admin guide)',
        'subtitle': 'Login, realms, clients, groups, and roles.',
    },
    'apps-overleaf.json': {
        'title': 'Overleaf',
        'subtitle': 'Login, wait for group access, and admin group setup.',
    },
}

# Simple phrase replacements for EN HTML (vi → en)
PHRASES = [
    ('Mở Dohub', 'Open Dohub'),
    ('Điều kiện', 'Prerequisites'),
    ('Tạo drive mới', 'Create a new drive'),
    ('Xóa drive', 'Delete drive'),
    ('Lưu ý', 'Note'),
    ('Không xóa drive đang được server đang chạy sử dụng', 'Do not delete a drive in use by a running server'),
    ('khi viết tài liệu hoặc demo', 'when writing docs or demos'),
    ('dùng tên có tiền tố', 'use names prefixed with'),
    ('và xóa ngay sau khi xong', 'and delete immediately when finished'),
    ('Tạo server', 'Create server'),
    ('Xóa server', 'Delete server'),
    ('Chờ admin', 'Wait for admin'),
    ('Đăng nhập', 'Sign in'),
    ('Hướng dẫn admin', 'Admin guide'),
    ('hoặc subdomain workspace tương ứng', 'or your workspace subdomain'),
    ('Cảnh báo', 'Warning'),
    ('chỉ chọn ổ dành riêng cho DirectPV', 'only select disks dedicated to DirectPV'),
    ('không phải OS disk', 'not the OS disk'),
    ('Trạng thái', 'Status'),
    ('hiển thị ngoài vùng terminal', 'shown outside the terminal area'),
    ('để tránh lệch con trỏ prompt', 'to avoid cursor offset in the prompt'),
    ('User có quyền', 'Users with permission'),
    ('Admin cấp quyền', 'Admin grants permission'),
    ('bật', 'enable'),
    ('Xem', 'See'),
]


def scrub_domains(text: str) -> str:
    for pat, repl in DOMAIN_MAP:
        text = re.sub(pat, repl, text)
    return text


def migrate_json(path: Path) -> None:
    data = json.loads(path.read_text(encoding='utf-8'))
    if 'vi' in data:
        return
    vi = {
        'section': data['section'],
        'title': data['title'],
        'subtitle': data['subtitle'],
    }
    en_extra = EN_META.get(path.name, {})
    en = {
        'section': EN_SECTION.get(data['section'], data['section']),
        'title': en_extra.get('title', data['title']),
        'subtitle': en_extra.get('subtitle', data['subtitle']),
    }
    out = {'href': data['href'], 'vi': vi, 'en': en}
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def vi_to_en_html(text: str) -> str:
    text = scrub_domains(text)
    for vi_p, en_p in PHRASES:
        text = text.replace(vi_p, en_p)
    return text


def main() -> None:
    EN.mkdir(parents=True, exist_ok=True)
    for jp in VI.glob('*.json'):
        migrate_json(jp)
    for jp in VI.glob('*.json'):
        text = jp.read_text(encoding='utf-8')
        jp.write_text(scrub_domains(text), encoding='utf-8')

    for hp in VI.glob('*.html'):
        vi_text = scrub_domains(hp.read_text(encoding='utf-8'))
        hp.write_text(vi_text, encoding='utf-8')
        en_path = EN / hp.name
        if hp.name == 'installation.html':
            en_path.write_text(vi_text, encoding='utf-8')
        else:
            en_path.write_text(vi_to_en_html(vi_text), encoding='utf-8')
    print('migrated', len(list(VI.glob('*.json'))), 'json,', len(list(EN.glob('*.html'))), 'en html')


if __name__ == '__main__':
    main()
