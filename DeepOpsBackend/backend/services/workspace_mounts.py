"""Multiple DirectPV drive mounts per workspace."""

from __future__ import annotations

from collections import Counter

from backend.models import User, UserDrive, Workspace, WorkspaceDriveMount
from backend.services.bulk import resolve_user_drive_ref


def normalize_mount_path(path: str) -> str:
    text = (path or '').strip() or '/home/coder'
    if not text.startswith('/'):
        text = '/' + text
    return text[:256]


def pvc_sub_path(mount_path: str) -> str:
    """subPath inside the PVC matches mountPath (no leading slash for Kubernetes)."""
    text = normalize_mount_path(mount_path)
    return text.lstrip('/') or text


def normalize_drive_mounts_data(data: dict) -> list[dict]:
    if 'drive_mounts' in data and isinstance(data['drive_mounts'], list):
        mounts = []
        for item in data['drive_mounts']:
            if not isinstance(item, dict):
                continue
            drive_ref = (
                item.get('drive_id')
                or item.get('user_drive_id')
                or item.get('claim_name')
                or item.get('drive_slug')
                or item.get('drive_name')
                or item.get('drive')
            )
            if not drive_ref:
                continue
            mounts.append({
                'drive_ref': str(drive_ref).strip(),
                'mount_path': normalize_mount_path(item.get('mount_path')),
            })
        return mounts

    drive_ref = (
        data.get('drive_id')
        or data.get('user_drive_id')
        or data.get('claim_name')
        or data.get('drive_slug')
        or data.get('drive_name')
        or data.get('drive')
    )
    if drive_ref:
        return [{
            'drive_ref': str(drive_ref).strip(),
            'mount_path': normalize_mount_path(data.get('mount_path')),
        }]
    return []


def drive_mounts_payload(workspace: Workspace) -> list[dict]:
    rows = []
    if workspace.user_drive_id and workspace.user_drive:
        drive = workspace.user_drive
        rows.append({
            'drive_id': str(workspace.user_drive_id),
            'drive_name': drive.name,
            'drive_size': drive.size,
            'mount_path': workspace.mount_path,
            'claim_name': drive.claim_name,
        })
    extra = workspace.extra_drive_mounts.select_related('user_drive').order_by('sort_order', 'created_at')
    for mount in extra:
        drive = mount.user_drive
        rows.append({
            'drive_id': str(mount.user_drive_id),
            'drive_name': drive.name,
            'drive_size': drive.size,
            'mount_path': mount.mount_path,
            'claim_name': drive.claim_name,
        })

    claim_counts = Counter(row['claim_name'] for row in rows)
    for row in rows:
        if claim_counts[row['claim_name']] > 1:
            row['sub_path'] = pvc_sub_path(row['mount_path'])
        else:
            row['sub_path'] = ''
    return rows


def spawn_drive_mounts(workspace: Workspace) -> list[dict]:
    """Mounts for Helm: claim_name, mount_path, optional sub_path (multi-path same PVC)."""
    mounts = []
    for row in drive_mounts_payload(workspace):
        mounts.append({
            'claim_name': row['claim_name'],
            'mount_path': row['mount_path'],
            'sub_path': row.get('sub_path') or '',
        })
    return mounts


def build_pvc_volume_specs(mount_entries: list[dict]) -> tuple[list[dict], list[dict]]:
    """One Kubernetes volume per PVC; reuse volume name for multiple mount paths."""
    volumes: list[dict] = []
    volume_mounts: list[dict] = []
    claim_to_volume: dict[str, str] = {}
    vol_counter = 0

    for entry in mount_entries:
        claim = entry['claim_name']
        if claim not in claim_to_volume:
            vol_name = 'workspace-volume' if vol_counter == 0 else f'drive-volume-{vol_counter}'
            claim_to_volume[claim] = vol_name
            volumes.append({
                'name': vol_name,
                'persistentVolumeClaim': {'claimName': claim},
            })
            vol_counter += 1

        vm: dict = {
            'name': claim_to_volume[claim],
            'mountPath': entry['mount_path'],
        }
        sub_path = (entry.get('sub_path') or '').strip()
        if sub_path:
            vm['subPath'] = sub_path
        volume_mounts.append(vm)

    return volumes, volume_mounts


def apply_drive_mounts_from_data(
    workspace: Workspace,
    owner: User,
    data: dict,
) -> str | None:
    mounts_data = normalize_drive_mounts_data(data)
    if not mounts_data:
        if workspace.user_drive_id:
            WorkspaceDriveMount.objects.filter(workspace=workspace).delete()
            workspace.user_drive = None
        return None

    seen_paths: set[str] = set()
    resolved: list[tuple[UserDrive, str]] = []

    for item in mounts_data:
        mount_path = item['mount_path']
        if mount_path in seen_paths:
            return 'duplicate mount path in mount list'
        seen_paths.add(mount_path)

        drive = resolve_user_drive_ref(owner, item['drive_ref'])
        if not drive:
            return f'drive not found: {item["drive_ref"]}'

        resolved.append((drive, mount_path))

    primary_drive, primary_path = resolved[0]
    workspace.user_drive = primary_drive
    workspace.mount_path = primary_path

    if workspace._state.adding:
        workspace._pending_extra_mounts = resolved[1:]
    else:
        _sync_extra_drive_mounts(workspace, resolved[1:])
    return None


def _sync_extra_drive_mounts(workspace: Workspace, extra: list[tuple[UserDrive, str]]) -> None:
    WorkspaceDriveMount.objects.filter(workspace=workspace).delete()
    for sort_order, (drive, mount_path) in enumerate(extra, start=1):
        WorkspaceDriveMount.objects.create(
            workspace=workspace,
            user_drive=drive,
            mount_path=mount_path,
            sort_order=sort_order,
        )


def persist_pending_drive_mounts(workspace: Workspace) -> None:
    pending = getattr(workspace, '_pending_extra_mounts', None)
    if pending is None:
        return
    _sync_extra_drive_mounts(workspace, pending)
    delattr(workspace, '_pending_extra_mounts')


def validate_workspace_drives_for_start(workspace: Workspace) -> str | None:
    """Block start when a drive is mounted by another running server (RWO PVC)."""
    from backend.models import UserDrive
    from backend.services.k8s_status import drive_is_in_use

    seen_drive_ids: set[str] = set()
    for row in drive_mounts_payload(workspace):
        drive_id = row['drive_id']
        if drive_id in seen_drive_ids:
            continue
        seen_drive_ids.add(drive_id)
        drive = UserDrive.objects.filter(id=drive_id).first()
        if not drive:
            continue
        if drive_is_in_use(drive, exclude_workspace_id=workspace.id):
            return f'drive in use by another running server: {drive.name}'
    return None
