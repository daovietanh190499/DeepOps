"""Normalize GitHub usernames for Kubernetes resource names (RFC 1123 labels)."""

from __future__ import annotations

import re

_LABEL_MAX_LEN = 63
_RFC1123_LABEL_RE = re.compile(r'^[a-z0-9]([-a-z0-9]*[a-z0-9])?$')


def normalize_resource_username(username: str, *, fallback: str = 'user') -> str:
    """Return a lowercase RFC 1123 label safe for K8s metadata.name segments."""
    text = (username or '').strip().lower()
    text = re.sub(r'[^a-z0-9-]', '-', text)
    text = re.sub(r'-+', '-', text).strip('-')
    if not text:
        text = fallback
    if not text[0].isalnum():
        text = f'u{text}'
    if not text[-1].isalnum():
        text = f'{text}0'
    if len(text) > _LABEL_MAX_LEN:
        text = text[:_LABEL_MAX_LEN].rstrip('-')
        if not text or not text[-1].isalnum():
            text = (text or fallback)[: _LABEL_MAX_LEN - 1].rstrip('-') + '0'
    if not _RFC1123_LABEL_RE.match(text):
        return fallback
    return text
