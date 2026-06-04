from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from backend.services.cluster import (
    get_cluster_overview,
    get_directpv_drives,
    get_k8s_nodes,
    get_microk8s_join_command,
)
from backend.services.github_auth import auth
from backend.views.drives import _require_admin


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
