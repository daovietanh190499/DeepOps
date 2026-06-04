"""Shared helpers for bulk drive / workspace import."""

from django.conf import settings

from backend.models import User, UserDrive, Workspace
from backend.services.drives_k8s import create_drive_pvc, normalize_size
from backend.services.k8s import build_spawn_config, create_codehub
from backend.services.k8s_status import live_drive_status, live_workspace_state


def resolve_user_drive(user: User, data: dict) -> UserDrive | None:
    drive_id = data.get('drive_id') or data.get('user_drive_id')
    if drive_id:
        drive = UserDrive.objects.filter(id=drive_id, user=user).first()
        if not drive and user.role == User.ROLE_ADMIN:
            drive = UserDrive.objects.filter(id=drive_id).first()
        return drive

    drive_slug = (data.get('drive_slug') or '').strip()
    if drive_slug:
        return UserDrive.objects.filter(user=user, slug=drive_slug).first()

    drive_name = (data.get('drive_name') or data.get('drive') or '').strip()
    if drive_name:
        drive = UserDrive.objects.filter(user=user, name__iexact=drive_name).first()
        if drive:
            return drive
        from django.utils.text import slugify

        slug = slugify(drive_name)
        if slug:
            return UserDrive.objects.filter(user=user, slug=slug).first()
    return None


def provision_user_drive(user: User, name: str, size: str) -> tuple[UserDrive | None, str | None, str]:
    """Create DB record and PVC. Returns (drive, error_message, logs)."""
    drive = UserDrive(user=user, name=name, size=size)
    drive.save()
    logs, code = create_drive_pvc(drive.claim_name, size, user.username, str(drive.id))
    if code != 0:
        drive.delete()
        return None, 'pvc create failed', logs
    return drive, None, logs


def spawn_workspace(ws: Workspace) -> dict | None:
    """Helm spawn for a workspace. Returns error dict on failure, else None."""
    if settings.DEFAULT_SPAWNER != 'k8s':
        return None
    try:
        config = build_spawn_config(ws)
    except ValueError as exc:
        return {'error': str(exc)}
    command, logs, exit_code = create_codehub(config)
    if exit_code != 0:
        return {
            'error': 'helm spawn failed',
            'logs': logs,
            'command': command,
            'exit_code': exit_code,
        }
    return None


def bulk_drive_result(drive: UserDrive, index: int) -> dict:
    return {
        'index': index,
        'ok': True,
        'id': str(drive.id),
        'name': drive.name,
        'slug': drive.slug,
        'claim_name': drive.claim_name,
        'size': drive.size,
        'status': live_drive_status(drive.claim_name),
    }


def bulk_workspace_result(ws: Workspace, index: int, *, auto_start: bool) -> dict:
    entry = {
        'index': index,
        'ok': True,
        'id': str(ws.id),
        'name': ws.name,
        'slug': ws.slug,
        'hostname': ws.hostname,
        'drive_id': str(ws.user_drive_id) if ws.user_drive_id else None,
        'state': live_workspace_state(ws) if auto_start else Workspace.STATE_OFFLINE,
    }
    return entry
