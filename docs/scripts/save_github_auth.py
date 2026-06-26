#!/usr/bin/env python3
"""Save GitHub OAuth session for docs screenshot capture (one-time manual login)."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / '.auth'
DOHUB = os.environ.get('DOHUB_URL', 'https://iaihub.uet.edu.vn').rstrip('/')


def main() -> None:
    role = (sys.argv[1] if len(sys.argv) > 1 else 'user').lower()
    if role not in ('user', 'admin'):
        raise SystemExit('Usage: save_github_auth.py [user|admin]')

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SystemExit('pip install playwright && playwright install chromium')

    env_sh = Path('/tmp/pw-libs/env.sh')
    if env_sh.exists():
        for line in env_sh.read_text().splitlines():
            if line.startswith('export LD_LIBRARY_PATH='):
                os.environ['LD_LIBRARY_PATH'] = line.split('=', 1)[1].strip().strip('"')

    headless = os.environ.get('DOCS_HEADLESS', '0') == '1'
    if headless:
        print('Cảnh báo: DOCS_HEADLESS=1 — không thể nhập OTP trong trình duyệt.', file=sys.stderr)
        print('Chạy: DOCS_HEADLESS=0 python3 scripts/save_github_auth.py', file=sys.stderr)

    AUTH.mkdir(parents=True, exist_ok=True)
    out = AUTH / f'{role}.json'

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=['--no-sandbox', '--disable-dev-shm-usage'],
        )
        context = browser.new_context(viewport={'width': 1440, 'height': 900})
        page = context.new_page()
        page.goto(f'{DOHUB}/login', wait_until='domcontentloaded', timeout=60000)
        print(f'Đăng nhập GitHub trong cửa sổ trình duyệt ({role}). Chờ redirect về Dohub…')
        page.wait_for_url(re.compile(r'iaihub\.uet\.edu\.vn'), timeout=600000)
        context.storage_state(path=str(out))
        browser.close()
    print('Đã lưu', out)


if __name__ == '__main__':
    main()
