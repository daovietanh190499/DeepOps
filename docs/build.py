#!/usr/bin/env python3
"""Generate static Dohub documentation wiki (bilingual VI/EN)."""

from __future__ import annotations

import html
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT_VI = ROOT / 'content' / 'vi'
CONTENT_EN = ROOT / 'content' / 'en'
LOCALES = ROOT / 'locales'
SITE_URL = 'https://daovietanh190499.github.io/DeepOps/docs/'
GITHUB_REPO = 'https://github.com/daovietanh190499/DeepOps'

PROSE_WRAPPER = 'doc-body prose prose-slate max-w-none prose-headings:font-semibold prose-a:text-blue-600'


def page_dir(href: str) -> Path:
    return Path(href).parent


def rel_link(from_href: str, to_href: str) -> str:
    start = page_dir(from_href)
    target = Path(to_href)
    rel = os.path.relpath(target, start=start if str(start) != '.' else '.')
    return rel.replace('\\', '/')


def asset_prefix(href: str) -> str:
    parts = page_dir(href).parts
    if not parts or parts == ('.',):
        return ''
    return '../' * len(parts)


def load_locale(lang: str) -> dict:
    path = LOCALES / f'{lang}.json'
    return json.loads(path.read_text(encoding='utf-8'))


def lang_block(vi: str, en: str) -> str:
    return (
        f'<div class="lang-block" data-lang="vi">{vi}</div>'
        f'<div class="lang-block hidden" data-lang="en">{en}</div>'
    )


def lang_text(vi: str, en: str) -> str:
    return lang_block(html.escape(vi), html.escape(en))


def img(path: str, alt_vi: str, alt_en: str, caption_vi: str = '', caption_en: str = '') -> str:
    cap_vi = (
        f'<figcaption class="mt-2 text-center text-sm text-slate-500">{html.escape(caption_vi)}</figcaption>'
        if caption_vi
        else ''
    )
    cap_en = (
        f'<figcaption class="mt-2 text-center text-sm text-slate-500">{html.escape(caption_en)}</figcaption>'
        if caption_en
        else ''
    )
    return (
        f'<figure class="my-6">'
        f'<img src="{html.escape(path)}" alt="{html.escape(alt_vi)}" '
        f'class="w-full rounded-xl border border-slate-200 shadow-sm" loading="lazy">'
        f'{lang_block(cap_vi, cap_en)}'
        f'</figure>'
    )


def note(vi: str, en: str, kind: str = 'info') -> str:
    colors = {
        'info': 'border-blue-200 bg-blue-50 text-blue-900',
        'warn': 'border-amber-200 bg-amber-50 text-amber-900',
        'danger': 'border-rose-200 bg-rose-50 text-rose-900',
    }
    cls = colors.get(kind, colors['info'])
    return f'<div class="my-4 rounded-xl border p-4 text-sm {cls}">{lang_block(vi, en)}</div>'


def flatten_nav(locale: dict) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    for section in locale['nav']:
        for href, label in section['items']:
            out.append((href, label, section['title']))
    return out


def render_nav(current_href: str, locale: dict) -> str:
    parts = ['<ul role="list" class="-ml-0.5 h-[calc(100vh-4.5rem)] overflow-y-auto py-7 pl-0.5 space-y-8">']
    for section in locale['nav']:
        parts.append(
            f'<li><h3 class="font-semibold tracking-tight text-slate-900">'
            f'{html.escape(section["title"])}</h3>'
        )
        parts.append('<ul role="list" class="pl-3 mt-3 space-y-2">')
        for href, label in section['items']:
            cls = 'text-blue-700 font-semibold' if href == current_href else 'text-slate-600 hover:text-slate-900'
            link = rel_link(current_href, href)
            parts.append(f'<li><a href="{link}" class="{cls}">{html.escape(label)}</a></li>')
        parts.append('</ul></li>')
    parts.append('</ul>')
    return '\n'.join(parts)


def render_nav_i18n(current_href: str, vi_loc: dict, en_loc: dict) -> str:
    parts = ['<ul role="list" class="-ml-0.5 h-[calc(100vh-4.5rem)] overflow-y-auto py-7 pl-0.5 space-y-8">']
    for vi_sec, en_sec in zip(vi_loc['nav'], en_loc['nav']):
        parts.append(
            '<li><h3 class="font-semibold tracking-tight text-slate-900">'
            f'{lang_text(vi_sec["title"], en_sec["title"])}'
            '</h3>'
        )
        parts.append('<ul role="list" class="pl-3 mt-3 space-y-2">')
        for (href, vi_label), (_, en_label) in zip(vi_sec['items'], en_sec['items']):
            cls = 'text-blue-700 font-semibold' if href == current_href else 'text-slate-600 hover:text-slate-900'
            link = rel_link(current_href, href)
            parts.append(
                f'<li><a href="{link}" class="{cls}">'
                f'{lang_text(vi_label, en_label)}'
                f'</a></li>'
            )
        parts.append('</ul></li>')
    parts.append('</ul>')
    return '\n'.join(parts)


def prev_next(current_href: str, vi_loc: dict, en_loc: dict) -> tuple[str, str]:
    pages = flatten_nav(vi_loc)
    idx = next(i for i, p in enumerate(pages) if p[0] == current_href)
    prev_block = ''
    next_block = ''
    if idx > 0:
        ph, pl_vi = pages[idx - 1][0], pages[idx - 1][1]
        pl_en = flatten_nav(en_loc)[idx - 1][1]
        prev_block = (
            f'<div class="mr-auto text-left"><dt class="text-sm text-slate-600">'
            f'{lang_text(vi_loc["ui"]["prev"], en_loc["ui"]["prev"])}</dt>'
            f'<dd class="mt-1"><a href="{rel_link(current_href, ph)}" class="font-semibold text-slate-900 hover:underline">'
            f'{lang_text(pl_vi, pl_en)}</a></dd></div>'
        )
    if idx < len(pages) - 1:
        nh, nl_vi = pages[idx + 1][0], pages[idx + 1][1]
        nl_en = flatten_nav(en_loc)[idx + 1][1]
        next_block = (
            f'<div class="ml-auto text-right"><dt class="text-sm text-slate-600">'
            f'{lang_text(vi_loc["ui"]["next"], en_loc["ui"]["next"])}</dt>'
            f'<dd class="mt-1"><a href="{rel_link(current_href, nh)}" class="font-semibold text-slate-900 hover:underline">'
            f'{lang_text(nl_vi, nl_en)}</a></dd></div>'
        )
    return prev_block, next_block


def lang_switcher() -> str:
    return '''<div class="flex items-center gap-1.5" role="group" aria-label="Language">
      <button type="button" data-lang-btn="vi" data-lang="vi" class="rounded-md px-2 py-1 text-lg leading-none hover:bg-slate-100" title="Tiếng Việt" aria-pressed="true">🇻🇳</button>
      <button type="button" data-lang-btn="en" data-lang="en" class="rounded-md px-2 py-1 text-lg leading-none hover:bg-slate-100" title="English" aria-pressed="false">🇬🇧</button>
    </div>'''


def rewrite_body_assets(body: str, href: str) -> str:
    prefix = asset_prefix(href)
    if not prefix:
        return body
    return body.replace('../assets/', f'{prefix}assets/')


def load_body_pair(name: str, page_href: str) -> str:
    vi_path = CONTENT_VI / name
    en_path = CONTENT_EN / name
    vi = rewrite_body_assets(vi_path.read_text(encoding='utf-8'), page_href) if vi_path.exists() else ''
    en = rewrite_body_assets(en_path.read_text(encoding='utf-8'), page_href) if en_path.exists() else vi
    return lang_block(vi, en)


def render_page(
    *,
    href: str,
    section_vi: str,
    section_en: str,
    title_vi: str,
    title_en: str,
    subtitle_vi: str,
    subtitle_en: str,
    body: str,
    vi_loc: dict,
    en_loc: dict,
) -> str:
    depth = asset_prefix(href)
    prev_block, next_block = prev_next(href, vi_loc, en_loc)
    nav = render_nav_i18n(href, vi_loc, en_loc)
    return f'''<!doctype html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(title_vi)} — Dohub Docs</title>
  <link rel="icon" href="{depth}assets/logo.png">
  <link rel="stylesheet" href="{depth}assets/docs.css">
  <script src="https://cdn.tailwindcss.com?plugins=forms"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>body {{ font-family: 'DM Sans', system-ui, sans-serif; }}</style>
</head>
<body class="bg-slate-50 text-slate-800 antialiased">
  <header class="sticky top-0 z-50 flex items-center justify-between gap-3 border-b border-slate-200 bg-white/95 px-4 py-2 shadow-sm backdrop-blur-sm">
    <a href="{rel_link(href, 'index.html')}" class="flex min-w-0 items-center gap-2.5">
      <img src="{depth}assets/logo.png" alt="Dohub" class="h-9 w-9 shrink-0 rounded-lg object-contain">
      <span class="truncate text-lg font-bold tracking-tight text-slate-900">Dohub <span class="font-medium text-slate-500">Docs</span></span>
    </a>
    <div class="flex shrink-0 items-center gap-2">
      {lang_switcher()}
      <a href="{GITHUB_REPO}" class="hidden rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 sm:inline-block">{html.escape(vi_loc["ui"]["github"])}</a>
    </div>
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
          <p class="text-sm font-medium text-slate-500">{lang_text(section_vi, section_en)}</p>
          <h1 class="text-3xl font-bold tracking-tight text-slate-900">{lang_text(title_vi, title_en)}</h1>
          <p class="mt-2 text-lg text-slate-600">{lang_text(subtitle_vi, subtitle_en)}</p>
        </header>
        <div class="mt-8 {PROSE_WRAPPER}">
{body}
        </div>
      </article>
      <dl class="mt-10 flex border-t border-slate-200 pt-6">{prev_block}{next_block}</dl>
    </div>
  </main>
  <script src="{depth}assets/docs.js"></script>
</body>
</html>'''


PAGES: list[dict] = []


def register_page(**kwargs) -> None:
    PAGES.append(kwargs)


def build_index(vi_loc: dict, en_loc: dict) -> None:
    cards = []
    for vi_sec, en_sec in zip(vi_loc['nav'], en_loc['nav']):
        for (href, vi_label), (_, en_label) in zip(vi_sec['items'], en_sec['items']):
            if href == 'index.html':
                continue
            cards.append(
                f'<li><a href="{rel_link("index.html", href)}" class="block rounded-xl border border-slate-200 bg-white px-5 py-4 shadow-sm hover:border-blue-300 hover:shadow-md">'
                f'<p class="text-xs font-semibold uppercase tracking-wide text-slate-400">'
                f'{lang_text(vi_sec["title"], en_sec["title"])}</p>'
                f'<p class="mt-1 font-bold text-slate-900">{lang_text(vi_label, en_label)}</p></a></li>'
            )
    ui_vi, ui_en = vi_loc['ui'], en_loc['ui']
    body = f'''
<p>{lang_block(ui_vi["index_lead"], ui_en["index_lead"])}</p>
{img('assets/logo.png', 'Logo Dohub', 'Dohub logo', ui_vi['index_logo_caption'], ui_en['index_logo_caption'])}
<div class="not-prose mt-8 grid gap-4 sm:grid-cols-2">
{''.join(cards)}
</div>
<h2>{lang_text(ui_vi['index_quick_links'], ui_en['index_quick_links'])}</h2>
<ul>
<li><strong>{lang_text('Mã nguồn', 'Source code')}:</strong> <a href="{GITHUB_REPO}">GitHub — DeepOps</a></li>
</ul>
{note(ui_vi['index_warn'], ui_en['index_warn'], 'warn')}
'''
    register_page(
        href='index.html',
        section_vi=vi_loc['nav'][0]['title'],
        section_en=en_loc['nav'][0]['title'],
        title_vi=vi_loc['ui']['index_title'],
        title_en=en_loc['ui']['index_title'],
        subtitle_vi=vi_loc['ui']['index_subtitle'],
        subtitle_en=en_loc['ui']['index_subtitle'],
        body=body,
    )


def main() -> None:
    vi_loc = load_locale('vi')
    en_loc = load_locale('en')
    build_index(vi_loc, en_loc)

    inst = vi_loc['pages']['installation.html']
    inst_en = en_loc['pages']['installation.html']
    register_page(
        href='installation.html',
        section_vi=inst['section'],
        section_en=inst_en['section'],
        title_vi=inst['title'],
        title_en=inst_en['title'],
        subtitle_vi=inst['subtitle'],
        subtitle_en=inst_en['subtitle'],
        body=load_body_pair('installation.html', 'installation.html'),
    )

    for fragment in sorted(CONTENT_VI.glob('*.html')):
        if fragment.name == 'installation.html':
            continue
        meta_path = CONTENT_VI / fragment.name.replace('.html', '.json')
        if not meta_path.exists():
            continue
        meta = json.loads(meta_path.read_text(encoding='utf-8'))
        register_page(
            href=meta['href'],
            section_vi=meta['vi']['section'],
            section_en=meta['en']['section'],
            title_vi=meta['vi']['title'],
            title_en=meta['en']['title'],
            subtitle_vi=meta['vi']['subtitle'],
            subtitle_en=meta['en']['subtitle'],
            body=load_body_pair(fragment.name, meta['href']),
        )

    for page in PAGES:
        out = ROOT / page['href']
        out.parent.mkdir(parents=True, exist_ok=True)
        html_out = render_page(**page, vi_loc=vi_loc, en_loc=en_loc)
        out.write_text(html_out, encoding='utf-8')
        print('wrote', out.relative_to(ROOT))

    for legacy in ('doc.html',):
        p = ROOT / legacy
        if p.exists():
            p.unlink()


if __name__ == '__main__':
    main()
