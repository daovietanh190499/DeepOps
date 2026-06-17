"""Parse container command strings with basic shell quoting support."""

from __future__ import annotations


def parse_container_command(raw) -> list[str]:
    """Parse command from JSON list or a shell-style string.

    Supports single- and double-quoted arguments, e.g.
    ``sh -c 'redis-server --requirepass $PASSWORD --appendonly yes'`` becomes
    ``['sh', '-c', 'redis-server --requirepass $PASSWORD --appendonly yes']``.
    """
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(c).strip() for c in raw if str(c).strip()]
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return []
        return _parse_shell_command(text)
    return []


def _parse_shell_command(text: str) -> list[str]:
    out: list[str] = []
    cur: list[str] = []
    quote: str | None = None
    i = 0
    while i < len(text):
        ch = text[i]
        if quote:
            if ch == quote:
                quote = None
            elif ch == '\\' and quote == '"' and i + 1 < len(text):
                i += 1
                cur.append(text[i])
            else:
                cur.append(ch)
        elif ch in ('"', "'"):
            quote = ch
        elif ch.isspace():
            if cur:
                out.append(''.join(cur))
                cur = []
        else:
            cur.append(ch)
        i += 1
    if cur:
        out.append(''.join(cur))
    return out


def format_container_command(parts) -> str:
    """Format command argv list back to a shell-style string for editing."""
    if not parts:
        return ''
    rendered: list[str] = []
    for part in parts:
        s = str(part)
        if not s:
            continue
        if any(c.isspace() for c in s) or '"' in s or "'" in s:
            rendered.append("'" + s.replace("'", "'\\''") + "'")
        else:
            rendered.append(s)
    return ' '.join(rendered)
