import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from backend.services.kubectl_cache import DEFAULT_TTL_SECONDS
from backend.services.cluster import (
    get_cluster_overview,
    get_directpv_drives,
    get_k8s_nodes,
    get_microk8s_join_command,
)
from backend.services.directpv_discover import (
    discover_drives,
    init_drives,
    read_drives_yaml,
    save_drives_yaml,
)
from backend.services.github_auth import auth
from backend.views.drives import _require_admin


def _parse_body(request) -> dict:
    if not request.body:
        return {}
    return json.loads(request.body.decode('utf-8'))


@auth.verify
@require_http_methods(['GET'])
def admin_cluster_overview(request, user):
    denied = _require_admin(user)
    if denied:
        return denied
    return JsonResponse({
        'result': {
            'cluster': get_cluster_overview(),
            'nodes': get_k8s_nodes(),
            'directpv': get_directpv_drives(),
            'cache_ttl_seconds': DEFAULT_TTL_SECONDS,
        },
    })


@auth.verify
@csrf_exempt
@require_http_methods(['POST'])
def admin_cluster_join_command(request, user):
    denied = _require_admin(user)
    if denied:
        return denied
    result = get_microk8s_join_command()
    status = 200 if result.get('ok') else 500
    return JsonResponse({'result': result}, status=status)


@auth.verify
@require_http_methods(['GET'])
def admin_directpv_discover(request, user):
    denied = _require_admin(user)
    if denied:
        return denied
    result = read_drives_yaml()
    status = 200 if result.get('ok') else 500
    return JsonResponse({'result': result}, status=status)


@auth.verify
@csrf_exempt
@require_http_methods(['POST'])
def admin_directpv_discover_run(request, user):
    denied = _require_admin(user)
    if denied:
        return denied
    try:
        result = discover_drives()
    except Exception as exc:
        return JsonResponse({'result': {'ok': False, 'error': str(exc)}}, status=200)
    return JsonResponse({'result': result}, status=200)


@auth.verify
@csrf_exempt
@require_http_methods(['PUT'])
def admin_directpv_discover_save(request, user):
    denied = _require_admin(user)
    if denied:
        return denied
    try:
        data = _parse_body(request)
    except json.JSONDecodeError:
        return JsonResponse({'message': 'invalid json'}, status=400)
    payload = data.get('data') if isinstance(data.get('data'), dict) else data
    result = save_drives_yaml(payload)
    status = 200 if result.get('ok') else 400
    return JsonResponse({'result': result}, status=status)


@auth.verify
@csrf_exempt
@require_http_methods(['POST'])
def admin_directpv_init(request, user):
    denied = _require_admin(user)
    if denied:
        return denied
    try:
        result = init_drives()
    except Exception as exc:
        return JsonResponse({'result': {'ok': False, 'error': str(exc)}}, status=200)
    return JsonResponse({'result': result}, status=200)
