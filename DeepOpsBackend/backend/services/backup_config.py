"""Workspace rclone backup configuration helpers."""

from __future__ import annotations

import re

from backend.models import Workspace
from backend.services.workspace_mounts import (
    build_pvc_volume_specs,
    drive_mounts_payload,
    normalize_mount_path,
    spawn_drive_mounts,
)

MAX_BACKUP_FOLDERS = 32
MAX_RCLONE_CONFIG_BYTES = 256 * 1024
CRON_RE = re.compile(
    r'^(\*|[0-9]+(?:-[0-9]+)?(?:/[0-9]+)?(?:,[0-9]+(?:-[0-9]+)?(?:/[0-9]+)?)*|\*/[0-9]+)\s+'
    r'(\*|[0-9]+(?:-[0-9]+)?(?:/[0-9]+)?(?:,[0-9]+(?:-[0-9]+)?(?:/[0-9]+)?)*|\*/[0-9]+)\s+'
    r'(\*|[0-9]+(?:-[0-9]+)?(?:/[0-9]+)?(?:,[0-9]+(?:-[0-9]+)?(?:/[0-9]+)?)*|\*/[0-9]+)\s+'
    r'(\*|[0-9]+(?:-[0-9]+)?(?:/[0-9]+)?(?:,[0-9]+(?:-[0-9]+)?(?:/[0-9]+)?)*|\*/[0-9]+)\s+'
    r'(\*|[0-9]+(?:-[0-9]+)?(?:/[0-9]+)?(?:,[0-9]+(?:-[0-9]+)?(?:/[0-9]+)?)*|\*/[0-9]+)$'
)
REMOTE_RE = re.compile(r'^[A-Za-z0-9_-]+:.+')


def backup_secret_name(workspace: Workspace) -> str:
    return f'{workspace.user.username}-{workspace.slug}-backup'


def workspace_backup_volume_options(workspace: Workspace) -> list[dict]:
    """PVCs and main-container mount paths the user may select for backup."""
    return [
        {
            'drive_id': row['drive_id'],
            'drive_name': row['drive_name'],
            'claim_name': row['claim_name'],
            'mount_path': row['mount_path'],
            'sub_path': row.get('sub_path') or '',
        }
        for row in drive_mounts_payload(workspace)
    ]


def allowed_backup_mount_paths(workspace: Workspace) -> set[str]:
    return {
        normalize_mount_path(row['mount_path']).rstrip('/') or '/'
        for row in workspace_backup_volume_options(workspace)
    }


def parse_backup_folders(raw) -> list[str]:
    if raw is None:
        return []
    items: list = []
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return []
        if text.startswith('['):
            import json
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError('folders must be valid JSON array') from exc
            if not isinstance(parsed, list):
                raise ValueError('folders must be a JSON array')
            items = parsed
        else:
            items = [part.strip() for part in text.replace(';', ',').split(',') if part.strip()]
    elif isinstance(raw, list):
        items = raw
    else:
        raise ValueError('folders must be a list or comma-separated string')

    folders: list[str] = []
    seen: set[str] = set()
    for item in items:
        path = str(item).strip()
        if not path:
            continue
        if not path.startswith('/'):
            raise ValueError(f'folder must be an absolute path: {path!r}')
        if '..' in path.split('/'):
            raise ValueError(f'folder must not contain .. segments: {path!r}')
        norm = path.rstrip('/') or '/'
        if norm in seen:
            continue
        seen.add(norm)
        folders.append(norm)
    if len(folders) > MAX_BACKUP_FOLDERS:
        raise ValueError(f'at most {MAX_BACKUP_FOLDERS} folders allowed')
    return folders


def parse_backup_mount_selection(workspace: Workspace, raw) -> list[str]:
    """Parse selected mount paths; each must match a workspace PVC mount."""
    folders = parse_backup_folders(raw)
    allowed = allowed_backup_mount_paths(workspace)
    if not allowed and folders:
        raise ValueError('workspace has no mounted volumes to back up')
    invalid = [path for path in folders if path not in allowed]
    if invalid:
        raise ValueError(
            'invalid backup volume(s): '
            + ', '.join(invalid)
            + ' — choose mount paths from the workspace drive list',
        )
    return folders


def backup_sidecar_volume_mounts(workspace: Workspace, mount_paths: list[str]) -> list[dict]:
    """Kubernetes volumeMounts for the backup sidecar (selected PVC paths only)."""
    selected = {normalize_mount_path(path).rstrip('/') or '/' for path in mount_paths}
    _, pvc_volume_mounts = build_pvc_volume_specs(spawn_drive_mounts(workspace))
    mounts: list[dict] = []
    for item in pvc_volume_mounts:
        mount_path = normalize_mount_path(item['mountPath']).rstrip('/') or '/'
        if mount_path not in selected:
            continue
        entry = {
            'name': item['name'],
            'mountPath': item['mountPath'],
        }
        if item.get('subPath'):
            entry['subPath'] = item['subPath']
        mounts.append(entry)
    return mounts


def validate_cron_schedule(schedule: str) -> str:
    text = (schedule or '').strip()
    if not text:
        raise ValueError('schedule is required (cron expression, e.g. 0 2 * * *)')
    if not CRON_RE.match(text):
        raise ValueError('invalid cron schedule — use five fields: minute hour day month weekday')
    return text


def validate_backup_remote(remote: str) -> str:
    text = (remote or '').strip()
    if not text:
        raise ValueError('remote destination is required (e.g. gdrive:backups/my-server)')
    if not REMOTE_RE.match(text):
        raise ValueError('remote must look like remote:path (e.g. gdrive:backups/workspace)')
    return text


def validate_rclone_config(config: str) -> str:
    text = (config or '').strip()
    if not text:
        raise ValueError('rclone config is required')
    if len(text.encode('utf-8')) > MAX_RCLONE_CONFIG_BYTES:
        raise ValueError(f'rclone config exceeds {MAX_RCLONE_CONFIG_BYTES // 1024} KiB')
    if not re.search(r'^\[[^\]]+\]\s*$', text, flags=re.MULTILINE):
        raise ValueError('rclone config must contain at least one [remote] section')
    return text + '\n'


def backup_config_from_workspace(workspace: Workspace) -> dict:
    allowed = allowed_backup_mount_paths(workspace)
    folders = [
        path for path in parse_backup_folders(workspace.backup_folders)
        if path in allowed
    ]
    return {
        'enabled': bool(workspace.backup_enabled),
        'schedule': workspace.backup_schedule or '',
        'remote': workspace.backup_remote or '',
        'folders': folders,
        'volume_options': workspace_backup_volume_options(workspace),
        'has_config': bool((workspace.backup_rclone_config or '').strip()),
        'secret_name': backup_secret_name(workspace),
    }


def backup_info_payload(workspace: Workspace, *, status: dict | None = None) -> dict:
    payload = backup_config_from_workspace(workspace)
    payload['rclone_config'] = workspace.backup_rclone_config or ''
    payload['status'] = status or {
        'last_run_at': '',
        'last_success': None,
        'last_message': '',
        'running': False,
        'trigger': '',
        'sidecar_active': False,
        'sidecar_ready': False,
        'service_active': bool(workspace.backup_enabled),
    }
    return payload
