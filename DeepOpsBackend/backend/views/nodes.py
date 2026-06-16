from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from backend.services.cluster import get_k8s_nodes
from backend.services.github_auth import auth
from backend.views.workspaces import _require_accepted


@auth.verify
@require_http_methods(['GET'])
def k8s_nodes(request, user):
    denied = _require_accepted(user)
    if denied:
        return denied

    summary = get_k8s_nodes()
    if not summary.get('ok'):
        return JsonResponse({'result': {'ok': False, 'nodes': [], 'error': summary.get('error') or 'failed to list nodes'}})

    nodes = summary.get('nodes') or []
    hostnames = []
    for node in nodes:
        if node.get('ready') != 'True':
            continue
        # Prefer the node name (matches kubectl node object); fall back to hostname/IP.
        hostnames.append(str(node.get('name') or node.get('hostname') or node.get('internal_ip') or '').strip())
    hostnames = [h for h in hostnames if h]
    hostnames = sorted(set(hostnames))

    return JsonResponse({'result': {'ok': True, 'nodes': hostnames}})

