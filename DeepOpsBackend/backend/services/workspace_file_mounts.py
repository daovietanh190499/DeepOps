"""Text file mounts stored in a Kubernetes ConfigMap per workspace."""

from __future__ import annotations

import json
import os

from backend.models import Workspace, WorkspaceFileMount
from backend.services.workspace_mounts import drive_mounts_payload, normalize_mount_path

FILE_MOUNT_MAX_BYTES = 1024 * 1024  # 1 MiB per file (UI + API)
CONFIGMAP_TOTAL_MAX_BYTES = 1024 * 1024  # Kubernetes ConfigMap size limit

ALLOWED_EXTENSIONS = (
    '.txt', '.js', '.json', '.env', '.yaml', '.yml', '.toml', '.ini', '.cfg',
    '.conf', '.properties', '.sh', '.py', '.md', '.xml', '.csv', '.ts', '.tsx',
    '.jsx', '.html', '.css', '.sql', '.gitignore', '.dockerignore', '.editorconfig',
    '.npmrc', '.prettierrc', '.eslintrc', '.lock', '.log', '.jsonc', '.hcl',
    '.tf', '.tfvars', '.pem', '.crt', '.key', '.pub', '.service', '.socket',
    '.mod', '.sum', '.go', '.rs', '.rb', '.php', '.java', '.kt', '.swift',
    '.c', '.cpp', '.h', '.hpp', '.vue', '.svelte', '.graphql', '.gql',
)

ALLOWED_BASENAMES = frozenset({
    'Dockerfile', 'Makefile', 'Gemfile', 'Rakefile', 'Procfile', 'Jenkinsfile',
    'LICENSE', 'README', 'CHANGELOG', 'AUTHORS', 'CONTRIBUTORS',
})


def _filename_allowed(filename: str) -> bool:
    base = os.path.basename((filename or '').strip())
    if not base:
        return False
    if base in ALLOWED_BASENAMES:
        return True
    lower = base.lower()
    return any(lower.endswith(ext) for ext in ALLOWED_EXTENSIONS)


def _validate_text_content(content: str) -> str | None:
    if content is None:
        return 'file content required'
    if '\x00' in content:
        return 'file must be text (no null bytes)'
    try:
        encoded = content.encode('utf-8')
    except UnicodeEncodeError:
        return 'file must be valid UTF-8 text'
    if len(encoded) > FILE_MOUNT_MAX_BYTES:
        return f'file exceeds {FILE_MOUNT_MAX_BYTES // 1024} KiB limit'
    return None


def configmap_key_for_index(index: int) -> str:
    return f'file-{index}'


def parse_template_file_mounts(raw) -> tuple[list[dict], str | None]:
    """Parse and validate file mounts for plan templates (filename, mount_path, content)."""
    if raw is None:
        return [], None
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return [], None
        try:
            raw = json.loads(text)
        except json.JSONDecodeError:
            return [], 'file_mounts must be valid JSON'
    if not isinstance(raw, list):
        return [], 'file_mounts must be a JSON array'

    mounts: list[dict] = []
    seen_paths: set[str] = set()
    total_bytes = 0

    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            return [], f'file_mounts[{index}] must be an object'
        filename = (item.get('filename') or '').strip()
        mount_path = normalize_mount_path(item.get('mount_path'))
        content = item.get('content')
        if content is None:
            content = ''
        if not isinstance(content, str):
            content = str(content)
        if not filename:
            return [], f'file_mounts[{index}]: filename required'
        if not _filename_allowed(filename):
            return [], f'file type not allowed: {filename}'
        err = _validate_text_content(content)
        if err:
            return [], f'{filename}: {err}'
        if mount_path in seen_paths:
            return [], f'duplicate mount path in file mount list: {mount_path}'
        seen_paths.add(mount_path)
        size = len(content.encode('utf-8'))
        total_bytes += size
        if total_bytes > CONFIGMAP_TOTAL_MAX_BYTES:
            return [], 'total file mount size exceeds ConfigMap limit (1 MiB)'
        mounts.append({
            'filename': os.path.basename(filename)[:255],
            'mount_path': mount_path,
            'content': content,
        })
    return mounts, None


def normalize_file_mounts_data(data: dict) -> list[dict]:
    raw = data.get('file_mounts')
    if not isinstance(raw, list):
        return []
    mounts: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        filename = (item.get('filename') or '').strip()
        mount_path = normalize_mount_path(item.get('mount_path'))
        content = item.get('content')
        if content is None:
            content = ''
        if not isinstance(content, str):
            content = str(content)
        mount_id = (item.get('id') or '').strip() or None
        if not filename and not mount_id:
            continue
        mounts.append({
            'id': mount_id,
            'filename': filename,
            'mount_path': mount_path,
            'content': content,
        })
    return mounts


def file_mounts_payload(workspace: Workspace, *, include_content: bool = True) -> list[dict]:
    rows = []
    for mount in workspace.file_mounts.order_by('sort_order', 'created_at'):
        row = {
            'id': str(mount.id),
            'filename': mount.filename,
            'mount_path': mount.mount_path,
            'configmap_key': mount.configmap_key,
            'size_bytes': len(mount.content.encode('utf-8')),
        }
        if include_content:
            row['content'] = mount.content
        rows.append(row)
    return rows


def _collect_mount_paths(workspace: Workspace) -> set[str]:
    paths = {row['mount_path'] for row in drive_mounts_payload(workspace)}
    return paths


def build_configmap_volume_specs(
    file_mounts: list[WorkspaceFileMount],
    configmap_name: str,
) -> tuple[list[dict], list[dict]]:
    if not file_mounts:
        return [], []

    items = []
    volume_mounts = []
    for mount in file_mounts:
        items.append({
            'key': mount.configmap_key,
            'path': mount.configmap_key,
        })
        volume_mounts.append({
            'name': 'file-mounts',
            'mountPath': mount.mount_path,
            'subPath': mount.configmap_key,
            'readOnly': True,
        })

    volumes = [{
        'name': 'file-mounts',
        'configMap': {
            'name': configmap_name,
            'defaultMode': 420,
            'items': items,
        },
    }]
    return volumes, volume_mounts


def apply_file_mounts_from_data(workspace: Workspace, data: dict) -> str | None:
    mounts_data = normalize_file_mounts_data(data)
    if 'file_mounts' not in data:
        return None

    seen_paths: set[str] = set()
    drive_paths = _collect_mount_paths(workspace)
    resolved: list[dict] = []
    total_bytes = 0

    for index, item in enumerate(mounts_data):
        mount_path = item['mount_path']
        if mount_path in seen_paths:
            return 'duplicate mount path in file mount list'
        if mount_path in drive_paths:
            return f'file mount path conflicts with drive mount: {mount_path}'
        seen_paths.add(mount_path)

        filename = item['filename']
        mount_id = item.get('id')
        existing = None
        if mount_id:
            existing = WorkspaceFileMount.objects.filter(
                workspace=workspace,
                id=mount_id,
            ).first()
            if not existing:
                return f'file mount not found: {mount_id}'
            if not filename:
                filename = existing.filename

        if not filename:
            return 'filename required for file mount'
        if not _filename_allowed(filename):
            return f'file type not allowed: {filename}'

        content = item['content']
        if existing and not content and mount_id:
            content = existing.content

        err = _validate_text_content(content)
        if err:
            return f'{filename}: {err}'

        size = len(content.encode('utf-8'))
        total_bytes += size
        if total_bytes > CONFIGMAP_TOTAL_MAX_BYTES:
            return 'total file mount size exceeds ConfigMap limit (1 MiB)'

        resolved.append({
            'filename': os.path.basename(filename)[:255],
            'configmap_key': configmap_key_for_index(index),
            'content': content,
            'mount_path': mount_path,
        })

    if workspace._state.adding:
        workspace._pending_file_mounts = resolved
    else:
        _sync_file_mounts(workspace, resolved)
    return None


def _sync_file_mounts(workspace: Workspace, mounts: list[dict]) -> None:
    WorkspaceFileMount.objects.filter(workspace=workspace).delete()
    for sort_order, item in enumerate(mounts):
        WorkspaceFileMount.objects.create(
            workspace=workspace,
            filename=item['filename'],
            configmap_key=item['configmap_key'],
            content=item['content'],
            mount_path=item['mount_path'],
            sort_order=sort_order,
        )


def persist_pending_file_mounts(workspace: Workspace) -> None:
    pending = getattr(workspace, '_pending_file_mounts', None)
    if pending is None:
        return
    _sync_file_mounts(workspace, pending)
    delattr(workspace, '_pending_file_mounts')
