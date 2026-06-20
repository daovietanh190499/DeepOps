import json
import re
import uuid

from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from backend.models import DockerImage, User, UserDrive, Workspace
from backend.services.github_auth import auth
from backend.services.k8s import get_codehub_workspace, remove_codehub, stop_codehub
from backend.services.bulk import bulk_workspace_result, spawn_workspace
from backend.services.k8s_status import (
    derive_workspace_state,
    live_workspace_k8s_status_batch,
    live_workspace_state,
    workspace_is_active,
)
from backend.services.gpu_resources import normalize_gpu_value
from backend.services.platform_catalog import parse_cpu_value
from backend.services.command_parse import parse_container_command
from backend.services.env_templates import expand_env_vars
from backend.services.resource_limits import can_change_privileged, validate_image_count, validate_server_count, validate_workspace_resources
from backend.services.workspace_kubectl import (
    MONITOR_DEFAULT_WINDOW_MINUTES,
    workspace_describe,
    workspace_logs,
    workspace_monitor_file,
    workspace_monitor_metrics,
)
from backend.services.workspace_file_mounts import (
    apply_file_mounts_from_data,
    file_mounts_payload,
    persist_pending_file_mounts,
)
from backend.services.workspace_files_k8s import delete_workspace_file_configmap
from backend.services.workspace_mounts import (
    apply_drive_mounts_from_data,
    drive_mounts_payload,
    persist_pending_drive_mounts,
)


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


def _parse_status_ids(request) -> list[str]:
    """Parse workspace/drive ids from POST JSON body: {ids: [...]} or {id: \"...\"}."""
    if not request.body:
        return []
    try:
        data = _parse_body(request)
    except json.JSONDecodeError:
        raise
    if not isinstance(data, dict):
        return []

    if 'ids' in data:
        raw_ids = data['ids']
        if isinstance(raw_ids, list):
            return [str(item).strip() for item in raw_ids if str(item).strip()]
        if isinstance(raw_ids, str) and raw_ids.strip():
            return [part.strip() for part in raw_ids.split(',') if part.strip()]
        return []

    if data.get('id'):
        return [str(data['id']).strip()]
    return []


def _workspace_list_payload(ws: Workspace) -> dict:
    """DB-only workspace row for list endpoints (no kubectl)."""
    data = ws.to_config_dict()
    data['state'] = Workspace.STATE_OFFLINE
    data['user_id'] = ws.user_id
    data['owner'] = ws.user.username
    data['created_at'] = ws.created_at.isoformat()
    data['updated_at'] = ws.updated_at.isoformat()
    data['drive_mounts'] = drive_mounts_payload(ws)
    data['file_mounts'] = file_mounts_payload(ws)
    return data


def _workspace_status_payloads(workspaces) -> list[dict]:
    ws_list = list(workspaces)
    k8s_map = live_workspace_k8s_status_batch(ws_list)
    empty = {
        'display': 'Not deployed',
        'deployment': None,
        'pods': [],
        'release_exists': False,
    }
    return [
        {
            'id': str(ws.id),
            'state': derive_workspace_state(k8s_map.get(str(ws.id), empty)),
            'k8s_status': k8s_map.get(str(ws.id), empty),
        }
        for ws in ws_list
    ]


def _workspace_status_payload(ws: Workspace) -> dict:
    """Live K8s status for a single workspace."""
    return _workspace_status_payloads([ws])[0]


def _workspace_payload(ws: Workspace, include_log: bool = False) -> dict:
    data = _workspace_list_payload(ws)
    data.update(_workspace_status_payload(ws))
    if include_log:
        data['pod_status'] = get_codehub_workspace(ws)
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


def _validate_workspace_limits(user: User, data: dict, ws: Workspace | None = None) -> str | None:
    cpu = data.get('cpu', ws.cpu if ws else 2)
    ram = data.get('ram', ws.ram if ws else '4G')
    gpu = normalize_gpu_value(data.get('gpu', ws.gpu if ws else ''))
    return validate_workspace_resources(user, cpu=cpu, ram=ram, gpu=gpu)


def _apply_workspace_fields(ws: Workspace, data: dict, owner: User | None = None) -> str | None:
    owner = owner or ws.user
    for field in ('name', 'ram', 'docker_repository', 'docker_tag'):
        if field in data and data[field] is not None:
            setattr(ws, field, data[field])
    if 'node_hostname' in data:
        ws.node_hostname = str(data.get('node_hostname') or '').strip()
    if 'cpu' in data and data['cpu'] is not None:
        try:
            ws.cpu = parse_cpu_value(data['cpu'])
        except ValueError:
            return 'invalid cpu'
    if 'gpu' in data:
        ws.gpu = normalize_gpu_value(data.get('gpu'))
    mount_fields = (
        'drive_mounts', 'drive_id', 'user_drive_id', 'drive_name', 'drive_slug', 'drive', 'mount_path',
    )
    if any(key in data for key in mount_fields):
        err = apply_drive_mounts_from_data(ws, owner, data)
        if err:
            return err
    if 'file_mounts' in data:
        err = apply_file_mounts_from_data(ws, data)
        if err:
            return err
    if 'env_vars' in data and isinstance(data['env_vars'], dict):
        ws.env_vars = expand_env_vars(data['env_vars'], owner.username)
    if 'exposed_ports' in data and isinstance(data['exposed_ports'], list):
        ws.exposed_ports = [int(p) for p in data['exposed_ports']]
    if 'container_command' in data:
        ws.container_command = parse_container_command(data['container_command'])
    if 'privileged' in data:
        requested = bool(data['privileged'])
        if requested and not can_change_privileged(owner):
            return 'privileged mode not allowed for your group'
        ws.privileged = requested if can_change_privileged(owner) else False
    return None


def _parse_docker_image_tags(data: dict) -> list[str]:
    tags = data.get('tags')
    if isinstance(tags, list):
        return [str(t).strip() for t in tags if str(t).strip()]
    text = (data.get('tags_text') or '').strip()
    if text:
        return [t for t in re.split(r'[\s,;]+', text) if t]
    default_tag = (data.get('default_tag') or 'latest').strip()
    return [default_tag] if default_tag else ['latest']


def _docker_image_fields(data: dict) -> tuple[dict | None, str | None]:
    label = (data.get('label') or '').strip()
    repository = (data.get('repository') or '').strip()
    if not label:
        return None, 'label required'
    if not repository:
        return None, 'repository required'

    tags = _parse_docker_image_tags(data)
    default_tag = (data.get('default_tag') or tags[0] or 'latest').strip()
    if default_tag not in tags:
        tags.insert(0, default_tag)

    return {
        'label': label[:255],
        'repository': repository[:512],
        'default_tag': default_tag[:128],
        'tags': tags,
        'is_active': bool(data.get('is_active', True)),
        'sort_order': int(data.get('sort_order', 0)),
    }, None


@auth.verify
@require_http_methods(['GET'])
def docker_images_list(request, user):
    denied = _require_accepted(user)
    if denied:
        return denied
    images = DockerImage.objects.filter(is_active=True, is_accepted=True)
    result = [img.to_dict() for img in images]
    return JsonResponse({'result': result})


@auth.verify
@require_http_methods(['GET'])
def my_docker_images(request, user):
    denied = _require_accepted(user)
    if denied:
        return denied
    page = max(1, int(request.GET.get('page', 1)))
    per_page = min(500, max(6, int(request.GET.get('per_page', 12))))
    name_filter = (request.GET.get('name') or '').strip()
    qs = DockerImage.objects.filter(created_by=user).select_related('created_by').order_by('-created_at', '-id')
    if name_filter:
        qs = qs.filter(label__icontains=name_filter)
    paginator = Paginator(qs, per_page)
    page_obj = paginator.get_page(page)
    return JsonResponse({
        'result': [img.to_dict() for img in page_obj.object_list],
        'pagination': {
            'page': page_obj.number,
            'per_page': per_page,
            'total': paginator.count,
            'pages': paginator.num_pages or 1,
        },
    })


@auth.verify
@csrf_exempt
@require_http_methods(['POST'])
def docker_image_create(request, user):
    denied = _require_accepted(user)
    if denied:
        return denied
    try:
        data = _parse_body(request)
    except json.JSONDecodeError:
        return JsonResponse({'message': 'invalid json'}, status=400)
    fields, err = _docker_image_fields(data)
    if err:
        return JsonResponse({'message': err}, status=400)
    limit_err = validate_image_count(user)
    if limit_err:
        return JsonResponse({'message': limit_err}, status=400)
    img = DockerImage.objects.create(
        **fields,
        created_by=user,
        is_accepted=False,
    )
    return JsonResponse({'result': img.to_dict()}, status=201)


@auth.verify
@csrf_exempt
@require_http_methods(['DELETE'])
def docker_image_delete(request, user, image_id):
    denied = _require_accepted(user)
    if denied:
        return denied
    img = DockerImage.objects.filter(id=image_id, created_by=user).first()
    if not img:
        return JsonResponse({'message': 'not found'}, status=404)
    img.delete()
    return JsonResponse({'message': 'success'})


@auth.verify
@require_http_methods(['GET'])
def my_workspaces(request, user):
    denied = _require_accepted(user)
    if denied:
        return denied

    page = max(1, int(request.GET.get('page', 1)))
    per_page = min(500, max(6, int(request.GET.get('per_page', 12))))
    name_filter = (request.GET.get('name') or '').strip()

    qs = Workspace.objects.filter(user=user).select_related('user', 'user_drive').order_by('-updated_at')
    if name_filter:
        qs = qs.filter(name__icontains=name_filter)

    paginator = Paginator(qs, per_page)
    page_obj = paginator.get_page(page)
    return JsonResponse({
        'result': [_workspace_list_payload(ws) for ws in page_obj.object_list],
        'pagination': {
            'page': page_obj.number,
            'per_page': per_page,
            'total': paginator.count,
            'pages': paginator.num_pages or 1,
        },
    })


@auth.verify
@csrf_exempt
@require_http_methods(['POST'])
def my_workspaces_status(request, user):
    denied = _require_accepted(user)
    if denied:
        return denied
    try:
        ids = _parse_status_ids(request)
    except json.JSONDecodeError:
        return JsonResponse({'message': 'invalid json'}, status=400)
    qs = Workspace.objects.filter(user=user)
    if ids:
        qs = qs.filter(id__in=ids)
    return JsonResponse({'result': _workspace_status_payloads(qs)})


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

    limit_err = validate_server_count(user) or _validate_workspace_limits(user, data)
    if limit_err:
        return JsonResponse({'message': limit_err}, status=400)

    ws = Workspace(user=user, name=name)
    err = _apply_workspace_fields(ws, data, owner=user)
    if err:
        return JsonResponse({'message': err}, status=400)
    ws.save()
    persist_pending_drive_mounts(ws)
    persist_pending_file_mounts(ws)
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
        if settings.DEFAULT_SPAWNER == 'k8s':
            exit_code = remove_codehub(ws.release_name)
            if exit_code != 0:
                return JsonResponse({'message': 'helm uninstall failed'}, status=500)
            delete_workspace_file_configmap(ws)
        ws.delete()
        return JsonResponse({'message': 'success'})

    if live_workspace_state(ws) != Workspace.STATE_OFFLINE:
        return JsonResponse({'message': 'stop server before editing'}, status=400)
    try:
        data = _parse_body(request)
    except json.JSONDecodeError:
        return JsonResponse({'message': 'invalid json'}, status=400)
    limit_err = _validate_workspace_limits(ws.user, data, ws=ws)
    if limit_err:
        return JsonResponse({'message': limit_err}, status=400)
    err = _apply_workspace_fields(ws, data)
    if err:
        return JsonResponse({'message': err}, status=400)
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


def _start_workspace(ws: Workspace, *, cleanup_on_failure: bool = False):
    spawn_err = spawn_workspace(ws)
    if spawn_err:
        if cleanup_on_failure:
            ws.delete()
        return JsonResponse({'message': spawn_err.get('error', 'spawn failed'), **spawn_err}, status=500)
    return JsonResponse({'message': 'success', 'result': _workspace_payload(ws)})


def _stop_workspace(ws: Workspace):
    try:
        if settings.DEFAULT_SPAWNER == 'k8s':
            logs, exit_code = stop_codehub(ws.release_name)
            if exit_code != 0:
                return JsonResponse({
                    'message': 'stop failed',
                    'logs': logs,
                }, status=500)
        return JsonResponse({'message': 'success', 'result': _workspace_payload(ws)})
    except Exception as exc:
        return JsonResponse({
            'message': 'stop failed',
            'error': str(exc),
        }, status=500)


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
    try:
        state = live_workspace_state(ws)
    except Exception:
        state = Workspace.STATE_RUNNING
    if not workspace_is_active(state):
        return JsonResponse({'message': 'not running'}, status=400)
    return _stop_workspace(ws)


@auth.verify
@require_http_methods(['GET'])
def workspace_logs_view(request, user, workspace_id):
    denied = _require_accepted(user)
    if denied:
        return denied
    ws, err = _get_workspace_for_user(user, workspace_id)
    if err:
        return err
    try:
        tail = int(request.GET.get('tail', '500') or 500)
    except (TypeError, ValueError):
        tail = 500
    pod = (request.GET.get('pod') or '').strip() or None
    container = (request.GET.get('container') or '').strip() or None
    return JsonResponse({'result': workspace_logs(ws, pod_name=pod, container=container, tail=tail)})


@auth.verify
@require_http_methods(['GET'])
def workspace_describe_view(request, user, workspace_id):
    denied = _require_accepted(user)
    if denied:
        return denied
    ws, err = _get_workspace_for_user(user, workspace_id)
    if err:
        return err
    pod = (request.GET.get('pod') or '').strip() or None
    return JsonResponse({'result': workspace_describe(ws, pod_name=pod)})


@auth.verify
@require_http_methods(['GET'])
def workspace_monitor_view(request, user, workspace_id):
    denied = _require_accepted(user)
    if denied:
        return denied
    ws, err = _get_workspace_for_user(user, workspace_id)
    if err:
        return err
    pod = (request.GET.get('pod') or '').strip() or None
    raw_window = (request.GET.get('window') or '').strip() or str(MONITOR_DEFAULT_WINDOW_MINUTES)
    return JsonResponse({
        'result': workspace_monitor_metrics(ws, pod_name=pod, window_minutes=raw_window),
    })


@auth.verify
@require_http_methods(['GET'])
def workspace_monitor_download_view(request, user, workspace_id):
    denied = _require_accepted(user)
    if denied:
        return denied
    ws, err = _get_workspace_for_user(user, workspace_id)
    if err:
        return err
    pod = (request.GET.get('pod') or '').strip() or None
    result = workspace_monitor_file(ws, pod_name=pod)
    if result.get('error'):
        return JsonResponse({'message': result['error']}, status=404)
    filename = result.get('filename') or 'metrics.tar.gz'
    content_type = result.get('content_type') or 'application/gzip'
    response = HttpResponse(result.get('content') or b'', content_type=content_type)
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


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
    limit_err = validate_server_count(user) or _validate_workspace_limits(user, data)
    if limit_err:
        return JsonResponse({'message': limit_err}, status=400)
    ws = Workspace(user=user, name=name)
    err = _apply_workspace_fields(ws, data, owner=user)
    if err:
        return JsonResponse({'message': err}, status=400)
    ws.save()
    persist_pending_drive_mounts(ws)
    persist_pending_file_mounts(ws)
    return _start_workspace(ws, cleanup_on_failure=True)


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
        limit_err = validate_server_count(user) or _validate_workspace_limits(user, item)
        if limit_err:
            results.append({'index': i, 'ok': False, 'error': limit_err, 'name': name})
            continue
        ws = Workspace(user=user, name=name)
        err = _apply_workspace_fields(ws, item, owner=user)
        if err:
            results.append({'index': i, 'ok': False, 'error': err, 'name': name})
            continue

        ws.save()
        persist_pending_drive_mounts(ws)
        persist_pending_file_mounts(ws)
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
    name_filter = (request.GET.get('name') or '').strip()
    group_filter = (request.GET.get('group') or '').strip()

    qs = Workspace.objects.select_related(
        'user',
        'user_drive',
        'user__resource_group_membership__group',
    ).order_by('-updated_at')
    if user_filter:
        qs = qs.filter(user__username__icontains=user_filter)
    if name_filter:
        qs = qs.filter(name__icontains=name_filter)
    if group_filter:
        if group_filter == '(none)':
            qs = qs.filter(user__resource_group_membership__isnull=True)
        else:
            # group filter may be UUID (group id) or group name substring
            try:
                group_id = uuid.UUID(group_filter)
            except (TypeError, ValueError):
                group_id = None
            if group_id is not None:
                qs = qs.filter(user__resource_group_membership__group_id=group_id)
            else:
                qs = qs.filter(user__resource_group_membership__group__name__icontains=group_filter)

    paginator = Paginator(qs, per_page)
    page_obj = paginator.get_page(page)
    return JsonResponse({
        'result': [_workspace_list_payload(ws) for ws in page_obj.object_list],
        'pagination': {
            'page': page_obj.number,
            'per_page': per_page,
            'total': paginator.count,
            'pages': paginator.num_pages or 1,
        },
    })


@auth.verify
@csrf_exempt
@require_http_methods(['POST'])
def admin_workspaces_status(request, user):
    denied = _require_admin(user)
    if denied:
        return denied
    try:
        ids = _parse_status_ids(request)
    except json.JSONDecodeError:
        return JsonResponse({'message': 'invalid json'}, status=400)
    qs = Workspace.objects.all()
    if ids:
        qs = qs.filter(id__in=ids)
    return JsonResponse({'result': _workspace_status_payloads(qs)})


@auth.verify
@require_http_methods(['GET'])
def admin_docker_images(request, user):
    denied = _require_admin(user)
    if denied:
        return denied
    name_filter = (request.GET.get('name') or '').strip()
    creator_filter = (request.GET.get('creator') or request.GET.get('user') or '').strip()
    status_filter = (request.GET.get('status') or '').strip().lower()
    page = max(1, int(request.GET.get('page', 1)))
    per_page = min(500, max(6, int(request.GET.get('per_page', 12))))

    images = DockerImage.objects.select_related('created_by').order_by('-created_at', '-id')
    if name_filter:
        images = images.filter(label__icontains=name_filter)
    if creator_filter:
        images = images.filter(created_by__username__icontains=creator_filter)
    if status_filter in ('accepted', 'accept', 'yes', 'true'):
        images = images.filter(is_accepted=True)
    elif status_filter in ('pending', 'not_accepted', 'no', 'false'):
        images = images.filter(is_accepted=False)

    paginator = Paginator(images, per_page)
    page_obj = paginator.get_page(page)
    return JsonResponse({
        'result': [img.to_dict() for img in page_obj.object_list],
        'pagination': {
            'page': page_obj.number,
            'per_page': per_page,
            'total': paginator.count,
            'pages': paginator.num_pages or 1,
        },
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
    fields, err = _docker_image_fields(data)
    if err:
        return JsonResponse({'message': err}, status=400)
    img = DockerImage.objects.create(**fields, is_accepted=True)
    return JsonResponse({'result': img.to_dict()}, status=201)


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
    if any(key in data for key in ('label', 'repository', 'default_tag', 'tags', 'tags_text', 'is_active', 'sort_order')):
        merged = {
            'label': data.get('label', img.label),
            'repository': data.get('repository', img.repository),
            'default_tag': data.get('default_tag', img.default_tag),
            'tags': data.get('tags', img.tags),
            'tags_text': data.get('tags_text', ''),
            'is_active': data.get('is_active', img.is_active),
            'sort_order': data.get('sort_order', img.sort_order),
        }
        fields, err = _docker_image_fields(merged)
        if err:
            return JsonResponse({'message': err}, status=400)
        for key, value in fields.items():
            setattr(img, key, value)
        img.save()
    if 'is_accepted' in data:
        img.is_accepted = bool(data.get('is_accepted'))
        img.save()
    return JsonResponse({'result': img.to_dict()})


@auth.verify
@require_http_methods(['GET'])
def admin_docker_images_export(request, user):
    denied = _require_admin(user)
    if denied:
        return denied
    images = DockerImage.objects.all().order_by('sort_order', 'label', 'id')
    payload = [img.to_dict() for img in images]
    content = json.dumps(payload, indent=2)
    response = HttpResponse(content, content_type='application/json')
    response['Content-Disposition'] = 'attachment; filename="dohub-docker-images.json"'
    return response


@auth.verify
@csrf_exempt
@require_http_methods(['POST'])
def admin_docker_images_import(request, user):
    """Bulk import docker images from JSON/CSV-parsed items.

    Upsert rules:
    - If id provided and exists: update that record
    - Else if repository+label matches an existing record (first match): update it
    - Else: create a new record
    """
    denied = _require_admin(user)
    if denied:
        return denied
    try:
        data = _parse_body(request)
    except json.JSONDecodeError:
        return JsonResponse({'message': 'invalid json'}, status=400)

    items = data.get('items') or []
    if not isinstance(items, list) or not items:
        return JsonResponse({'message': 'items required'}, status=400)

    results = []
    ok = 0
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            results.append({'index': idx, 'ok': False, 'error': 'invalid item'})
            continue

        try_id = str(item.get('id') or item.get('image_id') or '').strip()
        label = str(item.get('label') or '').strip()
        repo = str(item.get('repository') or item.get('repo') or '').strip()
        default_tag = str(item.get('default_tag') or item.get('tag') or '').strip()
        tags_text = str(item.get('tags_text') or item.get('tags') or '').strip()
        tags = item.get('tags')
        if isinstance(tags, str) and not tags_text:
            tags_text = tags
        sort_order = item.get('sort_order', 0)
        is_active = item.get('is_active', True)

        merged = {
            'label': label,
            'repository': repo,
            'default_tag': default_tag or 'latest',
            'tags': tags if isinstance(tags, list) else [],
            'tags_text': tags_text,
            'is_active': bool(is_active),
            'sort_order': int(sort_order or 0),
        }
        fields, err = _docker_image_fields(merged)
        if err:
            results.append({'index': idx, 'ok': False, 'error': err, 'label': label, 'repository': repo})
            continue

        img = None
        if try_id:
            try:
                img = DockerImage.objects.filter(id=int(try_id)).first()
            except ValueError:
                img = None
        if not img and repo and label:
            img = DockerImage.objects.filter(repository=repo, label=label).order_by('id').first()

        if img:
            for k, v in fields.items():
                setattr(img, k, v)
            img.save()
            out = img.to_dict()
        else:
            created = DockerImage.objects.create(**fields)
            out = created.to_dict()

        ok += 1
        results.append({'index': idx, 'ok': True, 'result': out})

    return JsonResponse({
        'message': 'success',
        'ok': ok,
        'failed': len(results) - ok,
        'results': results,
    })
