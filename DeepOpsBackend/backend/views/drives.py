import json

from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from backend.models import User, UserDrive, Workspace, WorkspaceDriveMount
from backend.services.drives_k8s import (
    delete_drive_pvc,
    get_pvc_info_map,
    normalize_size,
)
from backend.services.bulk import bulk_drive_result, provision_user_drive
from backend.services.k8s_status import drive_is_in_use, drive_status_from_pvc_phase, drives_in_use_map
from backend.services.github_auth import auth
from backend.services.resource_limits import validate_drive_count, validate_drive_size


def _require_accepted(user):
    if user is None:
        return JsonResponse({'message': 'no permission'}, status=403)
    if not user.is_accept:
        return JsonResponse({'message': 'no permission'}, status=403)
    return None


def _require_admin(user):
    denied = _require_accepted(user)
    if denied:
        return denied
    if user.role != User.ROLE_ADMIN:
        return JsonResponse({'message': 'no permission'}, status=403)
    return None


def _parse_body(request) -> dict:
    if not request.body:
        return {}
    return json.loads(request.body.decode('utf-8'))


def _parse_status_ids(request) -> list[str]:
    """Parse drive ids from POST JSON body: {ids: [...]} or {id: \"...\"}."""
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


def _drive_workspace_count(drive: UserDrive) -> int:
    ws_ids = set(Workspace.objects.filter(user_drive=drive).values_list('id', flat=True))
    ws_ids.update(
        WorkspaceDriveMount.objects.filter(user_drive=drive).values_list('workspace_id', flat=True),
    )
    return len(ws_ids)


def _drive_list_payload(drive: UserDrive) -> dict:
    """DB-only drive row for list endpoints (no kubectl)."""
    data = drive.to_dict()
    data['workspace_count'] = _drive_workspace_count(drive)
    data['pvc_phase'] = ''
    data['in_use'] = False
    data['node'] = ''
    data['pv_name'] = ''
    return data


def _drive_status_payload(
    drive: UserDrive,
    pvc_info: dict | None = None,
    in_use: bool | None = None,
) -> dict:
    if pvc_info is None:
        pvc_info = get_pvc_info_map([drive.claim_name]).get(
            drive.claim_name,
            {'phase': 'NotFound', 'node': '', 'pv_name': ''},
        )
    phase = pvc_info.get('phase', 'NotFound')
    if in_use is None:
        in_use = drive_is_in_use(drive)
    return {
        'id': str(drive.id),
        'status': drive_status_from_pvc_phase(phase),
        'pvc_phase': '' if phase == 'NotFound' else phase,
        'in_use': in_use,
        'node': pvc_info.get('node', '') or '',
        'pv_name': pvc_info.get('pv_name', '') or '',
    }


def _drive_payload(drive: UserDrive, pvc_info: dict | None = None, in_use: bool | None = None) -> dict:
    data = _drive_list_payload(drive)
    data.update(_drive_status_payload(drive, pvc_info=pvc_info, in_use=in_use))
    return data


def _drive_payloads(drives) -> list[dict]:
    drive_list = list(drives)
    pvc_map = get_pvc_info_map([d.claim_name for d in drive_list])
    in_use_map = drives_in_use_map(drive_list)
    return [
        _drive_payload(
            d,
            pvc_info=pvc_map.get(
                d.claim_name,
                {'phase': 'NotFound', 'node': '', 'pv_name': ''},
            ),
            in_use=in_use_map.get(str(d.id), False),
        )
        for d in drive_list
    ]


def _drive_list_payloads(drives) -> list[dict]:
    return [_drive_list_payload(d) for d in drives]


def _drive_status_payloads(drives) -> list[dict]:
    drive_list = list(drives)
    pvc_map = get_pvc_info_map([d.claim_name for d in drive_list])
    in_use_map = drives_in_use_map(drive_list)
    return [
        _drive_status_payload(
            d,
            pvc_info=pvc_map.get(
                d.claim_name,
                {'phase': 'NotFound', 'node': '', 'pv_name': ''},
            ),
            in_use=in_use_map.get(str(d.id), False),
        )
        for d in drive_list
    ]


@auth.verify
@require_http_methods(['GET'])
def my_drives(request, user):
    denied = _require_accepted(user)
    if denied:
        return denied

    page = max(1, int(request.GET.get('page', 1)))
    per_page = min(500, max(6, int(request.GET.get('per_page', 12))))
    name_filter = (request.GET.get('name') or '').strip()

    qs = UserDrive.objects.filter(user=user).order_by('-created_at')
    if name_filter:
        qs = qs.filter(name__icontains=name_filter)

    paginator = Paginator(qs, per_page)
    page_obj = paginator.get_page(page)
    return JsonResponse({
        'result': _drive_list_payloads(page_obj.object_list),
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
def my_drives_status(request, user):
    denied = _require_accepted(user)
    if denied:
        return denied
    try:
        ids = _parse_status_ids(request)
    except json.JSONDecodeError:
        return JsonResponse({'message': 'invalid json'}, status=400)
    qs = UserDrive.objects.filter(user=user)
    if ids:
        qs = qs.filter(id__in=ids)
    return JsonResponse({'result': _drive_status_payloads(qs)})


@auth.verify
@csrf_exempt
@require_http_methods(['POST'])
def drive_create(request, user):
    denied = _require_accepted(user)
    if denied:
        return denied
    try:
        data = _parse_body(request)
    except json.JSONDecodeError:
        return JsonResponse({'message': 'invalid json'}, status=400)

    name = (data.get('name') or 'My drive').strip()[:128]
    size = normalize_size(data.get('size') or '20Gi')
    limit_err = validate_drive_count(user) or validate_drive_size(user, size)
    if limit_err:
        return JsonResponse({'message': limit_err}, status=400)

    drive, err, logs = provision_user_drive(user, name, size)
    if err:
        return JsonResponse({'message': err, 'logs': logs}, status=500)

    return JsonResponse({'result': _drive_payload(drive)}, status=201)


@auth.verify
@csrf_exempt
@require_http_methods(['POST'])
def drive_bulk_create(request, user):
    """Create multiple DirectPV drives from JSON/CSV import."""
    denied = _require_accepted(user)
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
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            results.append({'index': i, 'ok': False, 'error': 'invalid item'})
            continue

        name = (item.get('name') or f'Drive {i + 1}').strip()[:128]
        if not name:
            results.append({'index': i, 'ok': False, 'error': 'name required'})
            continue

        size = normalize_size(item.get('size') or '20Gi')
        limit_err = validate_drive_count(user) or validate_drive_size(user, size)
        if limit_err:
            results.append({
                'index': i,
                'ok': False,
                'error': limit_err,
                'name': name,
            })
            continue
        drive, err, logs = provision_user_drive(user, name, size)
        if err:
            results.append({
                'index': i,
                'ok': False,
                'error': err,
                'name': name,
                'logs': logs,
            })
            continue

        results.append(bulk_drive_result(drive, i))

    ok_count = sum(1 for r in results if r.get('ok'))
    return JsonResponse({
        'message': 'success',
        'ok': ok_count,
        'failed': len(results) - ok_count,
        'results': results,
    })


@auth.verify
@csrf_exempt
@require_http_methods(['DELETE'])
def drive_delete(request, user, drive_id):
    denied = _require_accepted(user)
    if denied:
        return denied

    drive = UserDrive.objects.filter(id=drive_id).select_related('user').first()
    if not drive:
        return JsonResponse({'message': 'not found'}, status=404)
    if user.role != User.ROLE_ADMIN and drive.user_id != user.id:
        return JsonResponse({'message': 'no permission'}, status=403)

    if drive_is_in_use(drive):
        return JsonResponse({'message': 'drive in use by running server'}, status=400)

    delete_drive_pvc(drive.claim_name)
    Workspace.objects.filter(user_drive=drive).update(user_drive=None)
    WorkspaceDriveMount.objects.filter(user_drive=drive).delete()
    drive.delete()
    return JsonResponse({'message': 'success'})


@auth.verify
@require_http_methods(['GET'])
def admin_drives(request, user):
    denied = _require_admin(user)
    if denied:
        return denied

    page = max(1, int(request.GET.get('page', 1)))
    per_page = min(48, max(6, int(request.GET.get('per_page', 12))))
    user_filter = (request.GET.get('user') or '').strip()

    qs = UserDrive.objects.select_related('user').order_by('-created_at')
    if user_filter:
        qs = qs.filter(user__username__icontains=user_filter)

    paginator = Paginator(qs, per_page)
    page_obj = paginator.get_page(page)
    return JsonResponse({
        'result': _drive_list_payloads(page_obj.object_list),
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
def admin_drives_status(request, user):
    denied = _require_admin(user)
    if denied:
        return denied
    try:
        ids = _parse_status_ids(request)
    except json.JSONDecodeError:
        return JsonResponse({'message': 'invalid json'}, status=400)
    qs = UserDrive.objects.all()
    if ids:
        qs = qs.filter(id__in=ids)
    return JsonResponse({'result': _drive_status_payloads(qs)})
