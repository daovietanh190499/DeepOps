import json

from django.conf import settings
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from backend.models import DockerImage, User, UserDrive, Workspace
from backend.services.github_auth import auth
from backend.services.k8s import get_codehub_workspace, remove_codehub
from backend.services.bulk import (
    bulk_workspace_result,
    resolve_user_drive,
    spawn_workspace,
)
from backend.services.k8s_status import live_workspace_state, workspace_is_active
from backend.services.ssh_keys import ssh_info_payload


def _require_user(user):
    if user is None:
        return JsonResponse({'message': 'no permission'}, status=403)
    return None


def _require_admin(user):
    denied = _require_user(user)
    if denied:
        return denied
    if user.role != User.ROLE_ADMIN:
        return JsonResponse({'message': 'no permission'}, status=403)
    return None


def _require_accepted(user):
    denied = _require_user(user)
    if denied:
        return denied
    if not user.is_accept:
        return JsonResponse({'message': 'no permission'}, status=403)
    return None


def _workspace_payload(ws: Workspace, include_log: bool = False) -> dict:
    data = ws.to_config_dict()
    data['state'] = live_workspace_state(ws)
    data['user_id'] = ws.user_id
    data['owner'] = ws.user.username
    data['created_at'] = ws.created_at.isoformat()
    data['updated_at'] = ws.updated_at.isoformat()
    if include_log:
        data['pod_status'] = get_codehub_workspace(ws)
    data.update(ssh_info_payload(ws))
    return data


def _get_workspace_for_user(user, workspace_id):
    ws = Workspace.objects.filter(id=workspace_id).select_related('user', 'user_drive').first()
    if not ws:
        return None, JsonResponse({'message': 'not found'}, status=404)
    if user.role != User.ROLE_ADMIN and ws.user_id != user.id:
        return None, JsonResponse({'message': 'no permission'}, status=403)
    return ws, None


def _parse_body(request) -> dict:
    if not request.body:
        return {}
    return json.loads(request.body.decode('utf-8'))


def _apply_workspace_fields(ws: Workspace, data: dict, owner: User | None = None):
    owner = owner or ws.user
    for field in ('name', 'cpu', 'ram', 'gpu', 'docker_repository', 'docker_tag'):
        if field in data and data[field] is not None:
            setattr(ws, field, data[field])
    if 'mount_path' in data and data['mount_path']:
        ws.mount_path = str(data['mount_path']).strip()[:256] or '/home/coder'
    drive = resolve_user_drive(owner, data)
    if drive:
        ws.user_drive = drive
    if 'env_vars' in data and isinstance(data['env_vars'], dict):
        ws.env_vars = data['env_vars']
    if 'exposed_ports' in data and isinstance(data['exposed_ports'], list):
        ws.exposed_ports = [int(p) for p in data['exposed_ports']]
    if 'container_command' in data:
        cmd = data['container_command']
        if isinstance(cmd, str):
            ws.container_command = [c for c in cmd.split() if c]
        elif isinstance(cmd, list):
            ws.container_command = [str(c) for c in cmd]


@auth.verify
@require_http_methods(['GET'])
def docker_images_list(request, user):
    denied = _require_accepted(user)
    if denied:
        return denied
    images = DockerImage.objects.filter(is_active=True)
    result = [
        {
            'id': img.id,
            'label': img.label,
            'repository': img.repository,
            'default_tag': img.default_tag,
        }
        for img in images
    ]
    return JsonResponse({'result': result})


@auth.verify
@require_http_methods(['GET'])
def my_workspaces(request, user):
    denied = _require_accepted(user)
    if denied:
        return denied
    qs = Workspace.objects.filter(user=user).select_related('user', 'user_drive')
    return JsonResponse({
        'result': [_workspace_payload(ws) for ws in qs],
    })


@auth.verify
@csrf_exempt
@require_http_methods(['POST'])
def workspace_create(request, user):
    denied = _require_accepted(user)
    if denied:
        return denied
    try:
        data = _parse_body(request)
    except json.JSONDecodeError:
        return JsonResponse({'message': 'invalid json'}, status=400)

    name = (data.get('name') or 'Workspace').strip()[:128]
    if not name:
        return JsonResponse({'message': 'name required'}, status=400)

    ws = Workspace(user=user, name=name)
    _apply_workspace_fields(ws, data, owner=user)
    if not ws.user_drive_id:
        return JsonResponse({'message': 'drive_id required'}, status=400)
    ws.save()
    return JsonResponse({'result': _workspace_payload(ws)}, status=201)


@auth.verify
@csrf_exempt
@require_http_methods(['PUT', 'PATCH', 'DELETE'])
def workspace_detail(request, user, workspace_id):
    denied = _require_accepted(user)
    if denied:
        return denied
    ws, err = _get_workspace_for_user(user, workspace_id)
    if err:
        return err

    if request.method == 'DELETE':
        if workspace_is_active(live_workspace_state(ws)):
            if settings.DEFAULT_SPAWNER == 'k8s':
                remove_codehub(ws.release_name)
        ws.delete()
        return JsonResponse({'message': 'success'})

    if live_workspace_state(ws) != Workspace.STATE_OFFLINE:
        return JsonResponse({'message': 'stop server before editing'}, status=400)
    try:
        data = _parse_body(request)
    except json.JSONDecodeError:
        return JsonResponse({'message': 'invalid json'}, status=400)
    _apply_workspace_fields(ws, data)
    if data.get('name'):
        ws.name = data['name'].strip()[:128]
    ws.save()
    return JsonResponse({'result': _workspace_payload(ws)})


@auth.verify
@require_http_methods(['GET'])
def workspace_export(request, user, workspace_id):
    denied = _require_accepted(user)
    if denied:
        return denied
    ws, err = _get_workspace_for_user(user, workspace_id)
    if err:
        return err
    payload = _workspace_payload(ws)
    content = json.dumps(payload, indent=2)
    response = HttpResponse(content, content_type='application/json')
    response['Content-Disposition'] = (
        f'attachment; filename="dohub-{ws.slug}-config.json"'
    )
    return response


def _start_workspace(ws: Workspace):
    if not ws.user_drive_id:
        return JsonResponse({'message': 'select a drive to mount'}, status=400)
    spawn_err = spawn_workspace(ws)
    if spawn_err:
        return JsonResponse({'message': spawn_err.get('error', 'spawn failed'), **spawn_err}, status=500)
    return JsonResponse({'message': 'success', 'result': _workspace_payload(ws)})


def _stop_workspace(ws: Workspace):
    try:
        if settings.DEFAULT_SPAWNER == 'k8s':
            remove_codehub(ws.release_name)
    except Exception:
        return JsonResponse({'message': 'action failed'}, status=500)
    return JsonResponse({'message': 'success', 'result': _workspace_payload(ws)})


@auth.verify
@csrf_exempt
@require_http_methods(['POST'])
def workspace_start(request, user, workspace_id):
    denied = _require_accepted(user)
    if denied:
        return denied
    ws, err = _get_workspace_for_user(user, workspace_id)
    if err:
        return err
    state = live_workspace_state(ws)
    if state != Workspace.STATE_OFFLINE:
        return JsonResponse({'message': 'already running or pending'}, status=400)
    return _start_workspace(ws)


@auth.verify
@csrf_exempt
@require_http_methods(['POST'])
def workspace_stop(request, user, workspace_id):
    denied = _require_accepted(user)
    if denied:
        return denied
    ws, err = _get_workspace_for_user(user, workspace_id)
    if err:
        return err
    if not workspace_is_active(live_workspace_state(ws)):
        return JsonResponse({'message': 'not running'}, status=400)
    return _stop_workspace(ws)


@auth.verify
@csrf_exempt
@require_http_methods(['POST'])
def workspace_run(request, user):
    """Create workspace from form payload and start immediately."""
    denied = _require_accepted(user)
    if denied:
        return denied
    try:
        data = _parse_body(request)
    except json.JSONDecodeError:
        return JsonResponse({'message': 'invalid json'}, status=400)

    name = (data.get('name') or 'Workspace').strip()[:128]
    ws = Workspace(user=user, name=name)
    _apply_workspace_fields(ws, data, owner=user)
    if not ws.user_drive_id:
        return JsonResponse({'message': 'drive_id required'}, status=400)
    ws.save()
    return _start_workspace(ws)


@auth.verify
@csrf_exempt
@require_http_methods(['POST'])
def workspace_bulk_run(request, user):
    """Create (and optionally start) multiple workspaces from JSON/CSV import."""
    denied = _require_accepted(user)
    if denied:
        return denied
    try:
        data = _parse_body(request)
    except json.JSONDecodeError:
        return JsonResponse({'message': 'invalid json'}, status=400)

    items = data.get('items') or []
    auto_start = data.get('auto_start', True)
    if not isinstance(items, list) or not items:
        return JsonResponse({'message': 'items required'}, status=400)

    results = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            results.append({'index': i, 'ok': False, 'error': 'invalid item'})
            continue

        name = (item.get('name') or f'Workspace {i + 1}').strip()[:128]
        ws = Workspace(user=user, name=name)
        _apply_workspace_fields(ws, item, owner=user)

        if not ws.user_drive_id:
            drive_ref = item.get('drive_id') or item.get('drive_name') or item.get('drive_slug')
            err = 'drive_id, drive_name, or drive_slug required'
            if drive_ref:
                err = f'drive not found: {drive_ref}'
            results.append({'index': i, 'ok': False, 'error': err})
            continue

        ws.save()
        entry = bulk_workspace_result(ws, i, auto_start=auto_start)

        if auto_start:
            spawn_err = spawn_workspace(ws)
            if spawn_err:
                entry['ok'] = False
                entry.update(spawn_err)
            else:
                entry['state'] = live_workspace_state(ws)

        results.append(entry)

    ok_count = sum(1 for r in results if r.get('ok'))
    return JsonResponse({
        'message': 'success',
        'ok': ok_count,
        'failed': len(results) - ok_count,
        'results': results,
    })


@auth.verify
@require_http_methods(['GET'])
def admin_workspaces(request, user):
    denied = _require_admin(user)
    if denied:
        return denied

    page = max(1, int(request.GET.get('page', 1)))
    per_page = min(48, max(6, int(request.GET.get('per_page', 12))))
    user_filter = (request.GET.get('user') or '').strip()

    qs = Workspace.objects.select_related('user', 'user_drive').order_by('-updated_at')
    if user_filter:
        qs = qs.filter(user__username__icontains=user_filter)

    paginator = Paginator(qs, per_page)
    page_obj = paginator.get_page(page)
    return JsonResponse({
        'result': [_workspace_payload(ws) for ws in page_obj.object_list],
        'pagination': {
            'page': page_obj.number,
            'per_page': per_page,
            'total': paginator.count,
            'pages': paginator.num_pages or 1,
        },
    })


@auth.verify
@require_http_methods(['GET'])
def admin_docker_images(request, user):
    denied = _require_admin(user)
    if denied:
        return denied
    images = DockerImage.objects.all()
    return JsonResponse({
        'result': [
            {
                'id': img.id,
                'label': img.label,
                'repository': img.repository,
                'default_tag': img.default_tag,
                'is_active': img.is_active,
                'sort_order': img.sort_order,
            }
            for img in images
        ],
    })


@auth.verify
@csrf_exempt
@require_http_methods(['POST'])
def admin_docker_image_create(request, user):
    denied = _require_admin(user)
    if denied:
        return denied
    try:
        data = _parse_body(request)
    except json.JSONDecodeError:
        return JsonResponse({'message': 'invalid json'}, status=400)
    img = DockerImage.objects.create(
        label=data.get('label', 'Image'),
        repository=data.get('repository', ''),
        default_tag=data.get('default_tag', 'latest'),
        is_active=data.get('is_active', True),
        sort_order=data.get('sort_order', 0),
    )
    return JsonResponse({'result': {'id': img.id}}, status=201)


@auth.verify
@csrf_exempt
@require_http_methods(['PUT', 'PATCH', 'DELETE'])
def admin_docker_image_detail(request, user, image_id):
    denied = _require_admin(user)
    if denied:
        return denied
    img = DockerImage.objects.filter(id=image_id).first()
    if not img:
        return JsonResponse({'message': 'not found'}, status=404)
    if request.method == 'DELETE':
        img.delete()
        return JsonResponse({'message': 'success'})
    try:
        data = _parse_body(request)
    except json.JSONDecodeError:
        return JsonResponse({'message': 'invalid json'}, status=400)
    for field in ('label', 'repository', 'default_tag', 'is_active', 'sort_order'):
        if field in data:
            setattr(img, field, data[field])
    img.save()
    return JsonResponse({'message': 'success'})
