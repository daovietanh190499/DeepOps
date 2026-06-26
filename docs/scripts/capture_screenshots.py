#!/usr/bin/env python3
"""
Capture Dohub documentation screenshots with Playwright.

Usage:
  cp .env.capture.example .env.capture
  # Điền DOCS_USER_TOKEN / DOCS_ADMIN_TOKEN (GitHub PAT) — ưu tiên hơn mật khẩu
  bash scripts/run_capture.sh

Only creates/deletes resources named docs-demo-*.
Không chạy DirectPV discover/init (API bị chặn, không bấm nút Discover/Init).
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets' / 'screenshots'
CONTENT = ROOT / 'content'
AUTH = ROOT / '.auth'

DOHUB = os.environ.get('DOHUB_URL', 'https://iaihub.uet.edu.vn').rstrip('/')
KEYCLOAK = os.environ.get('KEYCLOAK_URL', 'https://keycloak.iaihub.uet.edu.vn').rstrip('/')
OVERLEAF = os.environ.get('OVERLEAF_URL', 'https://overleaf.iaihub.uet.edu.vn').rstrip('/')

ADMIN_USER = os.environ.get('DOCS_ADMIN_USER', 'agentdv')
ADMIN_PASS = os.environ.get('DOCS_ADMIN_PASS', '')
USER_NAME = os.environ.get('DOCS_USER', 'daovietanh99')
USER_PASS = os.environ.get('DOCS_USER_PASS', '')

DEMO_DRIVE = 'docs-demo-drive'
DEMO_SERVER = 'docs-demo-server'
DEMO_IMAGE_LABEL = 'docs-demo-image'

# Không được gọi discover/init DirectPV khi chụp docs.
DIRECTPV_BLOCKED_PATHS = (
    '/admin/cluster/directpv/discover/run',
    '/admin/cluster/directpv/discover/save',
    '/admin/cluster/directpv/init',
)
FORBIDDEN_BUTTON_LABELS = frozenset({'Discover', 'Init drives', 'Yes, init drives'})


def shot(page, name: str, *, full_page: bool = False) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f'{name}.png'
    page.screenshot(path=str(path), full_page=full_page)
    print('saved', path.name)


def wait_vue(page, ms: int = 1500) -> None:
    page.wait_for_timeout(ms)


def resolve_dohub_cookie(*, role: str = 'user') -> str:
    role_key = 'DOCS_ADMIN_COOKIE' if role == 'admin' else 'DOCS_USER_COOKIE'
    cookie = os.environ.get(role_key, '').strip()
    return cookie


def dohub_cookie_payload(access_key: str) -> dict:
    host = urlparse(DOHUB).hostname or 'iaihub.uet.edu.vn'
    return {
        'name': 'user_access_key',
        'value': access_key,
        'domain': host,
        'path': '/',
        'httpOnly': True,
        'secure': DOHUB.startswith('https'),
        'sameSite': 'Lax',
    }


def verify_dohub_session(page, username: str, *, admin: bool = False) -> bool:
    try:
        resp = page.request.get(f'{DOHUB}/user_state')
        if resp.status == 200:
            payload = resp.json().get('result') or {}
            if (payload.get('username') or '').lower() == username.lower():
                return True
    except Exception:
        pass
    if admin:
        return page.locator('nav').get_by_role('button', name='Overall', exact=True).count() > 0
    return page.get_by_role('button', name='My servers', exact=True).count() > 0


def open_workspace_detail(page, name: str) -> None:
    card = page.locator('.dohub-workspace-card').filter(has_text=name).first
    card.wait_for(state='visible', timeout=60000)
    card.click()
    page.locator('.dohub-modal-panel').wait_for(state='visible', timeout=30000)
    wait_vue(page, 2000)


def click_modal_tab(page, label: str) -> None:
    page.locator('.dohub-modal-tabs').get_by_role('button', name=label, exact=True).click()
    wait_vue(page, 2500)


def ensure_dohub_login(
    page,
    username: str,
    password: str,
    *,
    storage: Path | None = None,
    role: str = 'user',
) -> None:
    AUTH.mkdir(parents=True, exist_ok=True)

    if storage and storage.exists():
        print('using saved session', storage, flush=True)
        page.goto(DOHUB, wait_until='domcontentloaded', timeout=60000)
        wait_vue(page, 3000)
        if verify_dohub_session(page, username):
            return
        print('session hết hạn, đăng nhập lại…', flush=True)
        storage.unlink(missing_ok=True)

    cookie = resolve_dohub_cookie(role=role)
    if cookie:
        print(f'Đăng nhập Dohub bằng cookie ({username})…', flush=True)
        page.context.add_cookies([dohub_cookie_payload(cookie)])
        page.goto(DOHUB, wait_until='domcontentloaded', timeout=60000)
        wait_vue(page, 4000)
        if not verify_dohub_session(page, username, admin=(role == 'admin')):
            raise RuntimeError(f'Cookie Dohub không hợp lệ hoặc hết hạn cho {username}')
        if storage:
            page.context.storage_state(path=str(storage))
            print('saved auth', storage, flush=True)
        return

    github_login(page, username, password, storage=storage, role=role)


def resolve_github_token(username: str, *, role: str = 'user') -> str:
    role_key = 'DOCS_ADMIN_TOKEN' if role == 'admin' else 'DOCS_USER_TOKEN'
    token = os.environ.get(role_key, '').strip()
    if not token:
        token = os.environ.get('DOCS_GITHUB_TOKEN', '').strip()
    return token


def verify_github_token(token: str, username: str) -> None:
    try:
        import requests
    except ImportError:
        raise RuntimeError('pip install requests để dùng GitHub access token')

    resp = requests.get(
        'https://api.github.com/user',
        headers={
            'Authorization': f'Bearer {token}',
            'Accept': 'application/vnd.github+json',
        },
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f'Token GitHub không hợp lệ (HTTP {resp.status_code})')
    login = (resp.json().get('login') or '').lower()
    if login != username.lower():
        raise RuntimeError(f'Token thuộc @{resp.json().get("login")}, cần @{username}')


def prompt_github_otp(username: str, *, role: str = 'user') -> str:
    """Hỏi OTP khi GitHub đã hiện trang xác minh (sau khi nhập mật khẩu)."""
    env_key = 'DOCS_ADMIN_OTP' if role == 'admin' else 'DOCS_GITHUB_OTP'
    from_env = os.environ.get(env_key, '').strip()
    if from_env:
        return from_env
    if not sys.stdin.isatty():
        return ''
    print(flush=True)
    print('=' * 60, flush=True)
    print(f'  GitHub yêu cầu xác minh thiết bị: {username}', flush=True)
    print('  Mở email GitHub, lấy mã OTP rồi nhập bên dưới.', flush=True)
    print('=' * 60, flush=True)
    return input('  OTP: ').strip()


def wait_past_github_login(page) -> None:
    """Chờ GitHub xử lý sau submit (OTP / authorize / redirect)."""
    for _ in range(90):
        wait_vue(page, 1000)
        if re.search(r'iaihub\.uet\.edu\.vn', page.url):
            return
        if page.locator('button[name="authorize"]').count():
            return
        if 'verified-device' in page.url or page.locator('#otp').count():
            return
        if 'github.com/login/oauth' in page.url:
            return


def complete_github_otp_if_needed(page, username: str, *, role: str = 'user') -> None:
    if not ('verified-device' in page.url or page.locator('#otp').count()):
        return

    code = prompt_github_otp(username, role=role)
    if not code:
        raise RuntimeError('Cần mã OTP GitHub hoặc đặt DOCS_USER_TOKEN trong .env.capture')

    otp_input = page.locator('#otp')
    if otp_input.count():
        otp_input.fill(code)

    verify = page.locator('button:has-text("Verify")')
    if verify.count():
        try:
            verify.first.click(timeout=8000)
        except Exception:
            # OTP đã được xử lý và trang đã redirect (thường gặp)
            pass

    page.wait_for_url(
        re.compile(r'(github\.com/login/oauth|iaihub\.uet\.edu\.vn)'),
        timeout=120000,
    )


def github_login(
    page,
    username: str,
    password: str,
    *,
    storage: Path | None = None,
    role: str = 'user',
) -> None:
    AUTH.mkdir(parents=True, exist_ok=True)
    if storage and storage.exists():
        return

    token = resolve_github_token(username, role=role)
    secret = token or password
    if not username or not secret:
        raise SystemExit(
            'Thiếu thông tin đăng nhập. Đặt DOCS_USER_TOKEN (PAT) hoặc DOCS_USER_PASS trong .env.capture'
        )

    if token:
        verify_github_token(token, username)
        print(f'Đăng nhập GitHub bằng access token: {username}…', flush=True)
    else:
        print(f'Đăng nhập GitHub bằng mật khẩu: {username}…', flush=True)

    page.goto(f'{DOHUB}/login', wait_until='domcontentloaded', timeout=60000)
    wait_vue(page, 3000)
    if 'github.com' not in page.url:
        btn = page.get_by_role('button', name=re.compile(r'Login', re.I))
        if btn.count():
            btn.first.click()
            page.wait_for_url(re.compile(r'github\.com'), timeout=90000)

    # Đã vào Dohub (session còn hiệu lực)
    if re.search(r'iaihub\.uet\.edu\.vn', page.url) and 'login' not in page.url:
        if storage:
            page.context.storage_state(path=str(storage))
            print('saved auth', storage)
        return

    page.wait_for_selector('#login_field', timeout=60000)
    page.fill('#login_field', username)
    page.fill('#password', secret)
    page.click('input[type="submit"][name="commit"]')

    wait_past_github_login(page)
    complete_github_otp_if_needed(page, username, role=role)

    if page.locator('button[name="authorize"]').count():
        page.click('button[name="authorize"]')
    page.wait_for_url(re.compile(r'iaihub\.uet\.edu\.vn'), timeout=120000)
    wait_vue(page, 4000)
    if storage:
        page.context.storage_state(path=str(storage))
        print('saved auth', storage)


def click_tab(page, label: str) -> None:
    page.get_by_role('button', name=label, exact=True).first.click()
    wait_vue(page)


def click_admin_tab(page, label: str) -> None:
    page.locator('nav').get_by_role('button', name=label, exact=True).first.click()
    wait_vue(page)


def install_directpv_safety(page) -> None:
    """Chặn mọi API discover/init DirectPV — chỉ xem UI, không thao tác."""

    def handler(route, request) -> None:
        url = request.url
        if request.method in ('POST', 'PUT', 'PATCH') and any(p in url for p in DIRECTPV_BLOCKED_PATHS):
            print('blocked DirectPV API:', request.method, url, flush=True)
            route.abort('blockedbyclient')
            return
        route.continue_()

    page.route('**/*', handler)


def safe_click(page, locator, *, label: str = '') -> None:
    if label in FORBIDDEN_BUTTON_LABELS:
        raise RuntimeError(f'Forbidden button: {label}')
    locator.click()


def shot_directpv_section(page) -> None:
    """Chụp khu vực DirectPV — không bấm Discover / Init drives."""
    click_admin_tab(page, 'Overall')
    shot(page, 'admin-overall')
    heading = page.get_by_role('heading', name=re.compile(r'DirectPV', re.I))
    if heading.count():
        heading.first.scroll_into_view_if_needed()
    else:
        page.get_by_text('DirectPV discover', exact=False).first.scroll_into_view_if_needed()
    wait_vue(page, 1200)
    shot(page, 'admin-directpv-discover')
    # admin-directpv-init: không mở modal init (cần discover trước) — giữ placeholder SVG


def fill_input_placeholder(page, placeholder: str, value: str) -> None:
    page.locator(f'input[placeholder="{placeholder}"]').fill(value)


def capture_user_flow(page) -> None:
    storage = AUTH / 'user.json'
    ensure_dohub_login(page, USER_NAME, USER_PASS, storage=storage, role='user')
    shot(page, 'login')

    # Drives
    click_tab(page, 'My drives')
    shot(page, 'drives-list')
    page.get_by_role('button', name='Create drive', exact=True).click()
    wait_vue(page)
    fill_input_placeholder(page, 'Drive name', DEMO_DRIVE)
    shot(page, 'drives-create-modal')
    page.get_by_role('button', name='Create drive', exact=True).last.click()
    wait_vue(page, 3000)
    page.get_by_role('button', name='Delete drive').first.click()
    wait_vue(page)
    page.locator('input[placeholder="delete"]').fill('delete')
    shot(page, 'drives-delete-modal')
    page.get_by_role('button', name='Delete', exact=True).last.click()
    wait_vue(page, 2000)

    # Servers
    click_tab(page, 'My servers')
    shot(page, 'servers-list')
    delete_demo_server_if_exists(page)

    demo_card = page.locator('.dohub-workspace-card').filter(
        has=page.get_by_role('heading', name=DEMO_SERVER, exact=True)
    )
    if demo_card.count():
        print(f'using existing {DEMO_SERVER}', flush=True)
    else:
        page.get_by_role('button', name='Create server', exact=True).click()
        wait_vue(page, 2000)
        fill_input_placeholder(page, 'My workspace', DEMO_SERVER)
        shot(page, 'servers-create-modal')
        page.evaluate('window.scrollTo(0, 400)')
        wait_vue(page, 500)
        shot(page, 'servers-form-fields')
        domain_label = page.locator('label:has-text("Service domain")')
        if domain_label.count():
            domain_label.first.scroll_into_view_if_needed()
            wait_vue(page, 500)
            shot(page, 'custom-domain')
        page.get_by_role('button', name='Create server', exact=True).last.click()
        wait_vue(page, 5000)

    open_workspace_detail(page, DEMO_SERVER)

    for tab, name in [
        ('Logs', 'logs-tab'),
        ('Describe', 'describe-tab'),
        ('Terminal', 'terminal-tab'),
        ('Monitor', 'monitor-tab'),
        ('Backup', 'backup-tab'),
    ]:
        click_modal_tab(page, tab)
        shot(page, name)

    click_modal_tab(page, 'General')
    page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
    wait_vue(page, 500)
    shot(page, 'port-expose')

    page.keyboard.press('Escape')
    wait_vue(page, 1000)
    demo_card = page.locator('.dohub-workspace-card').filter(
        has=page.get_by_role('heading', name=DEMO_SERVER, exact=True)
    ).first
    stop_btn = demo_card.get_by_role('button', name='Stop', exact=True)
    if stop_btn.count():
        stop_btn.click()
        wait_vue(page, 8000)
    open_workspace_detail(page, DEMO_SERVER)
    click_modal_tab(page, 'General')
    edit_btn = page.locator('.dohub-modal-panel').get_by_role('button', name='Edit', exact=True)
    if edit_btn.count():
        edit_btn.click()
        wait_vue(page, 2000)
        shot(page, 'servers-edit-modal')
        page.get_by_role('button', name='Cancel', exact=True).click()
        wait_vue(page)

    page.keyboard.press('Escape')
    wait_vue(page, 1000)
    shot(page, 'servers-start-stop')

    try:
        card = page.locator('.dohub-workspace-card').filter(
            has=page.get_by_role('heading', name=DEMO_SERVER, exact=True)
        ).first
        card.locator('button[title="Delete"]').click(force=True, timeout=10000)
        wait_vue(page)
        page.locator('input[placeholder="delete"]').fill('delete')
        shot(page, 'servers-delete-modal')
        page.get_by_role('button', name='Delete', exact=True).last.click(force=True)
        wait_vue(page, 2000)
    except Exception as exc:
        print(f'could not capture servers-delete-modal: {exc}', flush=True)

    # Images
    try:
        click_tab(page, 'My images')
        shot(page, 'images-submit')
        fill_input_placeholder(page, 'Label', DEMO_IMAGE_LABEL)
        page.locator('input[placeholder="repository/name"]').fill('codercom/code-server')
        page.locator('input[placeholder="Default tag"]').fill('latest')
        page.locator('input[placeholder="Tags (comma-separated)"]').fill('latest')
        page.get_by_role('button', name='Submit image', exact=True).click()
        wait_vue(page, 2000)
        shot(page, 'images-pending')
        if page.get_by_role('button', name='Delete', exact=True).count():
            page.get_by_role('button', name='Delete', exact=True).first.click()
            wait_vue(page)
    except Exception as exc:
        print(f'images section skipped: {exc}', flush=True)


def delete_demo_server_if_exists(page) -> None:
    try:
        cards = page.locator('.dohub-workspace-card').filter(
            has=page.get_by_role('heading', name=DEMO_SERVER, exact=True)
        )
        if not cards.count():
            return
        del_btn = cards.first.locator('button[title="Delete"]')
        if not del_btn.count():
            print(f'skip delete {DEMO_SERVER} (no delete button)', flush=True)
            return
        del_btn.click(force=True, timeout=10000)
        wait_vue(page)
        confirm = page.locator('input[placeholder="delete"]')
        confirm.wait_for(state='visible', timeout=15000)
        confirm.fill('delete')
        page.get_by_role('button', name='Delete', exact=True).last.click(force=True)
        wait_vue(page, 3000)
    except Exception as exc:
        print(f'could not delete {DEMO_SERVER}: {exc}', flush=True)


def capture_admin_flow(page) -> None:
    storage = AUTH / 'admin.json'
    ensure_dohub_login(page, ADMIN_USER, ADMIN_PASS, storage=storage, role='admin')
    page.goto(DOHUB, wait_until='domcontentloaded', timeout=60000)
    wait_vue(page, 3000)
    if not verify_dohub_session(page, ADMIN_USER, admin=True):
        print('ADMIN: bỏ qua — session admin hết hạn, cập nhật DOCS_ADMIN_COOKIE', file=sys.stderr)
        return
    install_directpv_safety(page)

    shot_directpv_section(page)

    click_admin_tab(page, 'Drives')
    shot(page, 'admin-drives')

    click_admin_tab(page, 'Servers')
    shot(page, 'admin-servers')
    page.get_by_role('button', name='Catalog', exact=True).click()
    wait_vue(page)
    shot(page, 'admin-templates')

    click_admin_tab(page, 'Users')
    shot(page, 'admin-users')
    page.locator('select').filter(has=page.locator('option[value="pending"]')).first.select_option(
        value='pending'
    )
    wait_vue(page, 2000)
    accept_btn = page.locator('section').filter(
        has=page.get_by_role('heading', name='User management')
    ).get_by_role('button', name='Accept', exact=True)
    if accept_btn.count():
        shot(page, 'admin-accept-user')

    page.locator('section').filter(
        has=page.get_by_role('heading', name='User management')
    ).get_by_role('button', name='Groups', exact=True).click()
    wait_vue(page)
    shot(page, 'admin-groups')
    create_group = page.get_by_role('button', name='Create group', exact=True)
    if create_group.count():
        create_group.click()
        wait_vue(page)
        shot(page, 'admin-group-form')
        page.get_by_role('button', name='Cancel', exact=True).click()
        wait_vue(page)

    click_admin_tab(page, 'Images')
    shot(page, 'admin-images')
    page.locator('select').filter(has=page.locator('option[value="pending"]')).last.select_option(
        value='pending'
    )
    wait_vue(page, 2000)
    if page.get_by_role('button', name='Accept', exact=True).count():
        shot(page, 'admin-accept-image')


def capture_keycloak(page) -> None:
    page.goto(f'{KEYCLOAK}/admin/', wait_until='domcontentloaded', timeout=60000)
    wait_vue(page, 2000)
    shot(page, 'keycloak-login')
    # Admin login form varies — capture login page only if no creds
    admin_kc_user = os.environ.get('DOCS_KEYCLOAK_ADMIN', '')
    admin_kc_pass = os.environ.get('DOCS_KEYCLOAK_PASS', '')
    if admin_kc_user and admin_kc_pass:
        page.fill('#username', admin_kc_user)
        page.fill('#password', admin_kc_pass)
        page.click('#kc-login')
        wait_vue(page, 3000)
        shot(page, 'keycloak-realm')
        page.get_by_role('link', name=re.compile('Clients', re.I)).first.click()
        wait_vue(page)
        shot(page, 'keycloak-client')
        page.get_by_role('link', name=re.compile('Groups', re.I)).first.click()
        wait_vue(page)
        shot(page, 'keycloak-groups')


def capture_overleaf(page) -> None:
    page.goto(OVERLEAF, wait_until='domcontentloaded', timeout=60000)
    wait_vue(page, 3000)
    shot(page, 'overleaf-login')
    shot(page, 'overleaf-wait-group')
    shot(page, 'overleaf-admin-group')


def swap_content_images_to_png() -> None:
    for path in CONTENT.glob('*.html'):
        text = path.read_text(encoding='utf-8')

        def repl(match: re.Match) -> str:
            name = match.group(1)
            if (OUT / f'{name}.png').exists():
                return f'assets/screenshots/{name}.png'
            return match.group(0)

        new = re.sub(r'assets/screenshots/([a-z0-9-]+)\.svg', repl, text)
        if new != text:
            path.write_text(new, encoding='utf-8')
            print('updated', path.name)


def main() -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SystemExit('pip install playwright && playwright install chromium')

    env_sh = Path('/tmp/pw-libs/env.sh')
    if env_sh.exists():
        for line in env_sh.read_text().splitlines():
            if line.startswith('export LD_LIBRARY_PATH='):
                val = line.split('=', 1)[1].strip().strip('"')
                os.environ['LD_LIBRARY_PATH'] = val

    headless = os.environ.get('DOCS_HEADLESS', '1') != '0'
    chromium_path = os.environ.get('CHROMIUM_PATH', '')
    launch_kwargs: dict = {'headless': headless, 'args': ['--no-sandbox', '--disable-dev-shm-usage']}
    if chromium_path:
        launch_kwargs['executable_path'] = chromium_path
    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kwargs)

        user_storage = AUTH / 'user.json'
        uctx: dict = {'viewport': {'width': 1440, 'height': 900}}
        if user_storage.exists():
            uctx['storage_state'] = str(user_storage)
        elif resolve_dohub_cookie(role='user'):
            uctx['storage_state'] = {
                'cookies': [dohub_cookie_payload(resolve_dohub_cookie(role='user'))],
                'origins': [],
            }
        context = browser.new_context(**uctx)
        page = context.new_page()

        try:
            capture_user_flow(page)
        except Exception as exc:
            print('USER flow error:', exc, file=sys.stderr)

        admin_storage = AUTH / 'admin.json'
        actx: dict = {'viewport': {'width': 1440, 'height': 900}}
        if admin_storage.exists():
            actx['storage_state'] = str(admin_storage)
        elif resolve_dohub_cookie(role='admin'):
            actx['storage_state'] = {
                'cookies': [dohub_cookie_payload(resolve_dohub_cookie(role='admin'))],
                'origins': [],
            }
        context2 = browser.new_context(**actx)
        page = context2.new_page()
        try:
            capture_admin_flow(page)
        except Exception as exc:
            print('ADMIN flow error:', exc, file=sys.stderr)

        page = context2.new_page()
        try:
            capture_keycloak(page)
        except Exception as exc:
            print('KEYCLOAK flow error:', exc, file=sys.stderr)

        page = context.new_page()
        try:
            capture_overleaf(page)
        except Exception as exc:
            print('OVERLEAF flow error:', exc, file=sys.stderr)

        browser.close()

    swap_content_images_to_png()
    print('Done. Run: python3 build.py')


if __name__ == '__main__':
    main()
