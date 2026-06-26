#!/usr/bin/env python3
"""Generate static Dohub documentation wiki pages."""

from __future__ import annotations

import html
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / 'content'
ASSETS = ROOT / 'assets'
# GitHub Pages: https://<user>.github.io/DeepOps/docs/
SITE_URL = 'https://daovietanh190499.github.io/DeepOps/docs/'


def page_dir(href: str) -> Path:
    return Path(href).parent


def rel_link(from_href: str, to_href: str) -> str:
    """Relative URL from one generated page to another (works under /DeepOps/docs/)."""
    start = page_dir(from_href)
    target = Path(to_href)
    rel = os.path.relpath(target, start=start if str(start) != '.' else '.')
    return rel.replace('\\', '/')


def asset_prefix(href: str) -> str:
    """Prefix for assets/ from a page at href (e.g. '' or '../')."""
    parts = page_dir(href).parts
    if not parts or parts == ('.',):
        return ''
    return '../' * len(parts)


PROSE_CLASSES = (
    'prose prose-slate mt-8 max-w-none prose-headings:font-semibold prose-a:text-blue-600 '
    'prose-code:rounded prose-code:bg-slate-100 prose-code:px-1 '
    'prose-code:before:content-none prose-code:after:content-none '
    'prose-pre:bg-slate-900 prose-pre:text-slate-100 '
    'prose-pre:[&_code]:bg-transparent prose-pre:[&_code]:text-slate-100 '
    'prose-pre:[&_code]:p-0 prose-pre:[&_code]:before:content-none prose-pre:[&_code]:after:content-none'
)

NAV = [
    {
        'title': 'Bắt đầu',
        'items': [
            ('index.html', 'Tổng quan'),
            ('installation.html', 'Cài đặt cluster'),
        ],
    },
    {
        'title': 'Người dùng',
        'items': [
            ('user/drives.html', 'Tạo & xóa drive'),
            ('user/servers.html', 'Quản lý server'),
            ('user/images.html', 'Đăng ký Docker image'),
            ('user/port-expose.html', 'Expose port (wstunnel)'),
            ('user/logs-describe.html', 'Logs & Describe'),
            ('user/terminal.html', 'Terminal tương tác'),
            ('user/monitor.html', 'Monitor tài nguyên'),
            ('user/backup.html', 'Backup rclone'),
            ('user/custom-domain.html', 'Custom domain'),
        ],
    },
    {
        'title': 'Quản trị viên',
        'items': [
            ('admin/overall.html', 'Cluster overall'),
            ('admin/directpv.html', 'DirectPV discover & init'),
            ('admin/drives.html', 'Quản lý drives'),
            ('admin/servers.html', 'Quản lý servers'),
            ('admin/templates.html', 'Server templates'),
            ('admin/users.html', 'Users & accept'),
            ('admin/groups.html', 'Resource groups'),
            ('admin/docker-images.html', 'Docker images'),
        ],
    },
    {
        'title': 'Ứng dụng trên Dohub',
        'items': [
            ('apps/keycloak.html', 'Keycloak (admin)'),
            ('apps/overleaf.html', 'Overleaf'),
        ],
    },
]

FLAT_PAGES: list[tuple[str, str, str, str]] = []


def _flatten_nav() -> list[tuple[str, str, str, str]]:
    if FLAT_PAGES:
        return FLAT_PAGES
    for section in NAV:
        for href, label in section['items']:
            FLAT_PAGES.append((href, label, section['title'], href))
    return FLAT_PAGES


def img(path: str, alt: str, caption: str = '') -> str:
    cap = f'<figcaption class="mt-2 text-center text-sm text-slate-500">{html.escape(caption)}</figcaption>' if caption else ''
    return (
        f'<figure class="my-6">'
        f'<img src="{html.escape(path)}" alt="{html.escape(alt)}" '
        f'class="w-full rounded-xl border border-slate-200 shadow-sm" loading="lazy">'
        f'{cap}</figure>'
    )


def step(n: int, title: str, body: str) -> str:
    return (
        f'<section class="mt-10 border-t border-slate-200 pt-8">'
        f'<div class="flex items-center gap-3">'
        f'<span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-blue-600 text-sm font-bold text-white">{n}</span>'
        f'<h2 class="text-xl font-bold text-slate-900">{html.escape(title)}</h2></div>'
        f'<div class="prose prose-slate mt-4 max-w-none">{body}</div></section>'
    )


def note(text: str, kind: str = 'info') -> str:
    colors = {
        'info': 'border-blue-200 bg-blue-50 text-blue-900',
        'warn': 'border-amber-200 bg-amber-50 text-amber-900',
        'danger': 'border-rose-200 bg-rose-50 text-rose-900',
    }
    return f'<div class="my-4 rounded-xl border p-4 text-sm {colors.get(kind, colors["info"])}">{text}</div>'


def render_nav(current_href: str) -> str:
    parts = ['<ul role="list" class="-ml-0.5 h-[calc(100vh-4.5rem)] overflow-y-auto py-7 pl-0.5 space-y-8">']
    for section in NAV:
        parts.append(f'<li><h3 class="font-semibold tracking-tight text-slate-900">{html.escape(section["title"])}</h3>')
        parts.append('<ul role="list" class="pl-3 mt-3 space-y-2">')
        for href, label in section['items']:
            cls = 'text-blue-700 font-semibold' if href == current_href else 'text-slate-600 hover:text-slate-900'
            link = rel_link(current_href, href)
            parts.append(f'<li><a href="{link}" class="{cls}">{html.escape(label)}</a></li>')
        parts.append('</ul></li>')
    parts.append('</ul>')
    return '\n'.join(parts)


def prev_next(current_href: str) -> tuple[str | None, str | None, str | None, str | None]:
    pages = _flatten_nav()
    idx = next(i for i, p in enumerate(pages) if p[0] == current_href)
    prev_h, prev_l = (None, None)
    next_h, next_l = (None, None)
    if idx > 0:
        prev_h = rel_link(current_href, pages[idx - 1][0])
        prev_l = pages[idx - 1][1]
    if idx < len(pages) - 1:
        next_h = rel_link(current_href, pages[idx + 1][0])
        next_l = pages[idx + 1][1]
    return prev_h, prev_l, next_h, next_l


def render_page(
    *,
    href: str,
    section: str,
    title: str,
    subtitle: str,
    body: str,
) -> str:
    depth = asset_prefix(href)
    prev_h, prev_l, next_h, next_l = prev_next(href)
    nav = render_nav(href)
    prev_block = ''
    if prev_h:
        prev_block = (
            f'<div class="mr-auto text-left"><dt class="text-sm text-slate-600">Trước</dt>'
            f'<dd class="mt-1"><a href="{prev_h}" class="font-semibold text-slate-900 hover:underline">{html.escape(prev_l or "")}</a></dd></div>'
        )
    next_block = ''
    if next_h:
        next_block = (
            f'<div class="ml-auto text-right"><dt class="text-sm text-slate-600">Tiếp</dt>'
            f'<dd class="mt-1"><a href="{next_h}" class="font-semibold text-slate-900 hover:underline">{html.escape(next_l or "")}</a></dd></div>'
        )
    return f'''<!doctype html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(title)} — Dohub Docs</title>
  <link rel="icon" href="{depth}assets/logo.png">
  <script src="https://cdn.tailwindcss.com?plugins=forms,typography"></script>
  <script>
    tailwind.config = {{
      theme: {{ extend: {{ colors: {{ brand: {{ 500: '#3b82f6', 600: '#2563eb', 700: '#1d4ed8' }} }} }} }}
    }}
  </script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>body {{ font-family: 'DM Sans', system-ui, sans-serif; }}</style>
</head>
<body class="bg-slate-50 text-slate-800 antialiased">
  <header class="sticky top-0 z-50 flex items-center justify-between border-b border-slate-200 bg-white/95 px-4 py-2 shadow-sm backdrop-blur-sm">
    <a href="{rel_link(href, 'index.html')}" class="flex items-center gap-2.5">
      <img src="{depth}assets/logo.png" alt="Dohub" class="h-9 w-9 rounded-lg object-contain">
      <span class="text-lg font-bold tracking-tight text-slate-900">Dohub <span class="font-medium text-slate-500">Docs</span></span>
    </a>
    <a href="https://iaihub.uet.edu.vn/" class="hidden rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 sm:inline-block">Mở Dohub</a>
  </header>
  <main class="relative mx-auto flex max-w-8xl justify-center sm:px-2 lg:px-8 xl:px-12">
    <label for="navigation" class="fixed bottom-0 left-0 z-50 mb-4 ml-4 flex h-12 w-12 cursor-pointer items-center justify-center rounded-full border border-slate-300 bg-white text-slate-600 shadow-lg lg:hidden">
      <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-width="2" d="M4 8h16M4 16h16"/></svg>
    </label>
    <input type="checkbox" id="navigation" class="peer hidden">
    <div class="fixed left-0 top-[3.5rem] hidden h-screen px-4 shadow-xl peer-checked:block lg:relative lg:top-0 lg:block lg:h-auto lg:flex-none lg:px-0 lg:shadow-none">
      <div class="absolute inset-y-0 right-0 w-full bg-white lg:w-72 lg:bg-slate-50"></div>
      <nav class="sticky top-[4.5rem] w-64 pr-8 text-sm xl:w-72 xl:pr-16">{nav}</nav>
    </div>
    <div class="min-w-0 flex-auto max-w-3xl px-4 py-10 lg:max-w-none lg:pl-8 lg:pr-0 xl:px-16">
      <article>
        <header>
          <p class="text-sm font-medium text-slate-500">{html.escape(section)}</p>
          <h1 class="text-3xl font-bold tracking-tight text-slate-900">{html.escape(title)}</h1>
          <p class="mt-2 text-lg text-slate-600">{html.escape(subtitle)}</p>
        </header>
        <div class="{PROSE_CLASSES}">
{body}
        </div>
      </article>
      <dl class="mt-10 flex border-t border-slate-200 pt-6">{prev_block}{next_block}</dl>
    </div>
  </main>
</body>
</html>'''


def rewrite_body_assets(body: str, href: str) -> str:
    """Rewrite content asset paths for the page location under docs/."""
    prefix = asset_prefix(href)
    if not prefix:
        return body
    # content fragments use ../assets — from subdirs that's correct; from root use assets/
    return body.replace('../assets/', f'{prefix}assets/')


def load_fragment(name: str, *, page_href: str = '') -> str:
    path = CONTENT / name
    if path.exists():
        text = path.read_text(encoding='utf-8')
        if page_href:
            text = rewrite_body_assets(text, page_href)
        return text
    return f'<p><em>Missing content: {html.escape(name)}</em></p>'


def convert_installation() -> str:
    return load_fragment('installation.html', page_href='installation.html')


PAGES: list[dict] = []


def register(href: str, section: str, title: str, subtitle: str, body: str) -> None:
    PAGES.append({
        'href': href,
        'section': section,
        'title': title,
        'subtitle': subtitle,
        'body': body,
    })


def build_index() -> None:
    cards = []
    for sec in NAV:
        for href, label in sec['items']:
            if href == 'index.html':
                continue
            cards.append(
                f'<li><a href="{rel_link("index.html", href)}" class="block rounded-xl border border-slate-200 bg-white px-5 py-4 shadow-sm hover:border-blue-300 hover:shadow-md">'
                f'<p class="text-xs font-semibold uppercase tracking-wide text-slate-400">{html.escape(sec["title"])}</p>'
                f'<p class="mt-1 font-bold text-slate-900">{html.escape(label)}</p></a></li>'
            )
    body = f'''
<p>Dohub là nền tảng hub quản lý workspace <strong>code-server</strong> (và các container tùy chỉnh) trên Kubernetes.
Tài liệu này hướng dẫn cài đặt cluster, sử dụng tính năng người dùng, quản trị viên và các ứng dụng triển khai trên nền Dohub.</p>
{img('assets/logo.png', 'Logo Dohub', 'Dohub — workspace hub trên Kubernetes')}
<div class="not-prose mt-8 grid gap-4 sm:grid-cols-2">
{''.join(cards)}
</div>
<h2>Liên kết nhanh</h2>
<ul>
<li><strong>Hub production:</strong> <a href="https://iaihub.uet.edu.vn/">iaihub.uet.edu.vn</a></li>
<li><strong>Keycloak:</strong> <a href="https://keycloak.iaihub.uet.edu.vn/">keycloak.iaihub.uet.edu.vn</a></li>
<li><strong>Overleaf:</strong> <a href="https://overleaf.iaihub.uet.edu.vn/">overleaf.iaihub.uet.edu.vn</a></li>
<li><strong>Repository:</strong> <a href="https://github.com/daovietanh190499/DeepOps">GitHub — DeepOps</a></li>
</ul>
{note('Khi làm theo hướng dẫn có thao tác tạo/xóa, hãy dùng tên tạm (ví dụ <code>docs-demo-*</code>) và xóa ngay sau khi chụp ảnh — không chỉnh sửa tài nguyên production đang chạy.', 'warn')}
'''
    register('index.html', 'Bắt đầu', 'Tổng quan Dohub', 'Tài liệu chính thức cho người dùng và quản trị viên.', body)


def main() -> None:
    build_index()
    register(
        'installation.html',
        'Bắt đầu',
        'Cài đặt cluster',
        'Hướng dẫn triển khai MicroK8s, DirectPV, HAMi và Dohub từ đầu.',
        convert_installation(),
    )
    for fragment in sorted(CONTENT.glob('*.html')):
        if fragment.name == 'installation.html':
            continue
        meta_path = fragment.with_suffix('.json')
        if not meta_path.exists():
            continue
        import json
        meta = json.loads(meta_path.read_text(encoding='utf-8'))
        register(
            meta['href'],
            meta['section'],
            meta['title'],
            meta['subtitle'],
            rewrite_body_assets(fragment.read_text(encoding='utf-8'), meta['href']),
        )

    legacy_install = ROOT / 'installation.html'
    # installation.html is generated output; source is content/installation.html

    for page in PAGES:
        out = ROOT / page['href']
        out.parent.mkdir(parents=True, exist_ok=True)
        html_out = render_page(
            href=page['href'],
            section=page['section'],
            title=page['title'],
            subtitle=page['subtitle'],
            body=page['body'],
        )
        out.write_text(html_out, encoding='utf-8')
        print('wrote', out.relative_to(ROOT))

    # remove legacy template files after build
    for legacy in ('doc.html',):
        p = ROOT / legacy
        if p.exists():
            p.unlink()
            print('removed', legacy)


if __name__ == '__main__':
    main()
