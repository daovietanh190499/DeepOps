from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from backend.services.backup_config import (
    backup_info_payload,
    parse_backup_mount_selection,
    validate_backup_remote,
    validate_cron_schedule,
    validate_rclone_config,
)
from backend.services.backup_k8s import sync_workspace_backup_to_cluster
from backend.services.github_auth import auth
from backend.services.workspace_kubectl import workspace_backup_status, workspace_backup_trigger
from backend.views.workspaces import _get_workspace_for_user, _parse_body, _require_accepted


@auth.verify
@require_http_methods(['GET'])
def workspace_backup_info(request, user, workspace_id):
    denied = _require_accepted(user)
    if denied:
        return denied
    ws, err = _get_workspace_for_user(user, workspace_id)
    if err:
        return err
    status = workspace_backup_status(ws)
    return JsonResponse({'result': backup_info_payload(ws, status=status)})


@auth.verify
@csrf_exempt
@require_http_methods(['POST'])
def workspace_backup_schedule(request, user, workspace_id):
    denied = _require_accepted(user)
    if denied:
        return denied
    ws, err = _get_workspace_for_user(user, workspace_id)
    if err:
        return err

    try:
        data = _parse_body(request)
    except Exception:
        data = {}

    try:
        schedule = validate_cron_schedule(data.get('schedule', ws.backup_schedule))
        remote = validate_backup_remote(data.get('remote', ws.backup_remote))
        folders = parse_backup_mount_selection(ws, data.get('folders', ws.backup_folders))
        rclone_config = validate_rclone_config(
            data.get('rclone_config', ws.backup_rclone_config)
        )
    except ValueError as exc:
        return JsonResponse({'message': str(exc)}, status=400)

    if not folders:
        return JsonResponse({'message': 'select at least one volume to back up'}, status=400)

    current_status = workspace_backup_status(ws)
    if current_status.get('running'):
        return JsonResponse({'message': 'cannot schedule while a backup is running'}, status=400)

    if ws.backup_enabled or current_status.get('sidecar_active'):
        return JsonResponse({
            'message': 'backup sidecar is already active — click Stop backup to remove it first',
        }, status=400)

    ws.backup_schedule = schedule
    ws.backup_remote = remote
    ws.backup_folders = folders
    ws.backup_rclone_config = rclone_config
    ws.backup_enabled = True
    ws.save(update_fields=[
        'backup_schedule', 'backup_remote', 'backup_folders',
        'backup_rclone_config', 'backup_enabled', 'updated_at',
    ])

    sync = sync_workspace_backup_to_cluster(ws, respawn=True)
    status = workspace_backup_status(ws)
    payload = backup_info_payload(ws, status=status)
    payload['sync'] = sync

    if not sync.get('ok'):
        return JsonResponse({
            'message': sync.get('error') or 'settings saved but cluster sync failed',
            'result': payload,
        }, status=200)

    return JsonResponse({
        'message': sync.get('message') or 'Backup sidecar scheduled',
        'result': payload,
    })


@auth.verify
@csrf_exempt
@require_http_methods(['POST'])
def workspace_backup_run(request, user, workspace_id):
    denied = _require_accepted(user)
    if denied:
        return denied
    ws, err = _get_workspace_for_user(user, workspace_id)
    if err:
        return err

    if not ws.backup_enabled:
        return JsonResponse({'message': 'backup is not scheduled yet — click Schedule first'}, status=400)

    if not (ws.backup_remote or '').strip():
        return JsonResponse({
            'message': 'remote destination is required — set Remote destination and click Schedule',
        }, status=400)

    current_status = workspace_backup_status(ws)
    if current_status.get('running'):
        return JsonResponse({'message': 'a backup is already running'}, status=400)

    trigger = workspace_backup_trigger(ws)
    status = workspace_backup_status(ws)
    payload = backup_info_payload(ws, status=status)
    payload['trigger'] = trigger

    if not trigger.get('ok'):
        return JsonResponse({
            'message': trigger.get('error') or 'failed to start backup',
            'result': payload,
        }, status=400)

    return JsonResponse({
        'message': 'Backup started',
        'result': payload,
    })


@auth.verify
@csrf_exempt
@require_http_methods(['POST'])
def workspace_backup_stop_view(request, user, workspace_id):
    """Remove the backup sidecar from the workspace pod."""
    denied = _require_accepted(user)
    if denied:
        return denied
    ws, err = _get_workspace_for_user(user, workspace_id)
    if err:
        return err

    current_status = workspace_backup_status(ws)
    sidecar_active = bool(
        current_status.get('sidecar_active') or current_status.get('sidecar_ready')
    )

    if not ws.backup_enabled and not sidecar_active:
        return JsonResponse({'message': 'backup sidecar is not active'}, status=400)

    ws.backup_enabled = False
    ws.save(update_fields=['backup_enabled', 'updated_at'])

    sync = sync_workspace_backup_to_cluster(ws, respawn=True)
    status = workspace_backup_status(ws)
    payload = backup_info_payload(ws, status=status)
    payload['sync'] = sync

    if not sync.get('ok'):
        ws.backup_enabled = True
        ws.save(update_fields=['backup_enabled', 'updated_at'])
        return JsonResponse({
            'message': sync.get('error') or 'failed to remove backup sidecar',
            'result': payload,
        }, status=400)

    return JsonResponse({
        'message': sync.get('message') or 'Backup sidecar removed',
        'result': payload,
    })


@auth.verify
@csrf_exempt
@require_http_methods(['POST'])
def workspace_backup_save_config(request, user, workspace_id):
    """Persist backup form fields to DB without enabling the backup sidecar."""
    denied = _require_accepted(user)
    if denied:
        return denied
    ws, err = _get_workspace_for_user(user, workspace_id)
    if err:
        return err

    try:
        data = _parse_body(request)
    except Exception:
        data = {}

    update_fields = ['updated_at']

    try:
        if 'rclone_config' in data:
            text = str(data.get('rclone_config') or '')
            ws.backup_rclone_config = validate_rclone_config(text) if text.strip() else ''
            update_fields.append('backup_rclone_config')
        if 'remote' in data:
            remote = str(data.get('remote') or '').strip()
            ws.backup_remote = validate_backup_remote(remote) if remote else ''
            update_fields.append('backup_remote')
        if 'schedule' in data:
            schedule = str(data.get('schedule') or '').strip()
            ws.backup_schedule = validate_cron_schedule(schedule) if schedule else ''
            update_fields.append('backup_schedule')
        if 'folders' in data:
            ws.backup_folders = parse_backup_mount_selection(ws, data.get('folders'))
            update_fields.append('backup_folders')
    except ValueError as exc:
        return JsonResponse({'message': str(exc)}, status=400)

    if len(update_fields) == 1:
        return JsonResponse({'message': 'nothing to save'}, status=400)

    ws.save(update_fields=update_fields)

    status = workspace_backup_status(ws)
    return JsonResponse({
        'message': 'backup settings saved',
        'result': backup_info_payload(ws, status=status),
    })


@auth.verify
@require_http_methods(['GET'])
def workspace_backup_download_config(request, user, workspace_id):
    denied = _require_accepted(user)
    if denied:
        return denied
    ws, err = _get_workspace_for_user(user, workspace_id)
    if err:
        return err

    config = (ws.backup_rclone_config or '').strip()
    if not config:
        return JsonResponse({'message': 'no rclone config saved'}, status=404)

    if not config.endswith('\n'):
        config += '\n'
    filename = f'dohub-{ws.slug}-rclone.conf'
    response = HttpResponse(config, content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
