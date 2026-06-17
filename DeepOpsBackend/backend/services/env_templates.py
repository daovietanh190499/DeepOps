"""Expand <<rdstring:N>>, <<rdnum:N>>, <<tmsp>>, <<username>> placeholders in env values."""

from __future__ import annotations

import re
import secrets
import string
from datetime import datetime, timezone

ENV_TEMPLATE_RE = re.compile(r'<<([a-z]+)(?::(\d+))?>>', re.IGNORECASE)
_RDSTRING_ALPHABET = string.ascii_lowercase + string.digits


def _random_string(length: int) -> str:
    n = max(1, length)
    return ''.join(secrets.choice(_RDSTRING_ALPHABET) for _ in range(n))


def _random_digits(length: int) -> str:
    n = max(1, length)
    return ''.join(secrets.choice(string.digits) for _ in range(n))


def expand_env_template_value(value, username: str = '') -> str:
    text = '' if value is None else str(value)

    def repl(match: re.Match[str]) -> str:
        kind = match.group(1).lower()
        arg = int(match.group(2)) if match.group(2) else 0
        if kind == 'rdstring':
            return _random_string(arg if arg > 0 else 16)
        if kind == 'rdnum':
            return _random_digits(arg if arg > 0 else 6)
        if kind == 'tmsp':
            return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        if kind == 'username':
            return username
        return match.group(0)

    return ENV_TEMPLATE_RE.sub(repl, text)


def expand_env_vars(env: dict | None, username: str = '') -> dict:
    if not isinstance(env, dict):
        return {}
    out = {}
    for key, value in env.items():
        if key == 'PASSWORD_PREFIX':
            continue
        out[str(key)] = expand_env_template_value(value, username)
    if 'PASSWORD_PREFIX' in env and 'PASSWORD' not in out:
        prefix = str(env.get('PASSWORD_PREFIX', ''))
        out['PASSWORD'] = expand_env_template_value(f'{prefix}<<rdstring:6>>', username)
    return out
