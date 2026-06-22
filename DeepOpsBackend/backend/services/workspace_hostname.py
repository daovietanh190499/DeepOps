"""Custom workspace ingress hostname validation."""

from __future__ import annotations

import re

from backend.models import Workspace

_LABEL_RE = re.compile(r'^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$', re.I)


def normalize_custom_hostname(raw) -> str:
    value = (raw or '').strip().lower()
    if value.endswith('.'):
        value = value[:-1]
    return value


def validate_custom_hostname(value: str) -> str | None:
    host = normalize_custom_hostname(value)
    if not host:
        return None
    if len(host) > 253:
        return 'invalid hostname'
    if any(ch in host for ch in ' /:@'):
        return 'invalid hostname'
    labels = host.split('.')
    if not labels:
        return 'invalid hostname'
    for label in labels:
        if not label or len(label) > 63 or not _LABEL_RE.match(label):
            return 'invalid hostname'
    return None


def validate_custom_hostname_unique(hostname: str, workspace_id=None) -> str | None:
    host = normalize_custom_hostname(hostname)
    if not host:
        return None
    qs = Workspace.objects.filter(custom_hostname__iexact=host)
    if workspace_id:
        qs = qs.exclude(id=workspace_id)
    if qs.exists():
        return 'hostname already in use by another server'
    return None
