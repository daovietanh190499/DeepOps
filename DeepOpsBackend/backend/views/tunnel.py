from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from backend.services.github_auth import auth
from backend.services.tunnel_k8s import sync_workspace_tunnel_to_cluster
from backend.services.tunnel_ports import parse_tunnel_ports, tunnel_info_payload
from backend.views.workspaces import _get_workspace_for_user, _parse_body, _require_accepted


@auth.verify
@require_http_methods(['GET'])
def workspace_tunnel_info(request, user, workspace_id):
    denied = _require_accepted(user)
    if denied:
        return denied
    ws, err = _get_workspace_for_user(user, workspace_id)
    if err:
        return err
    return JsonResponse({'result': tunnel_info_payload(ws)})


@auth.verify
@csrf_exempt
@require_http_methods(['POST'])
def workspace_tunnel_expose(request, user, workspace_id):
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

    raw_ports = data.get('ports', data.get('ports_text', data.get('ws_tunnel_ports')))
    try:
        ports = parse_tunnel_ports(raw_ports)
    except ValueError as exc:
        return JsonResponse({'message': str(exc)}, status=400)

    ws.ws_tunnel_ports = ports
    ws.save(update_fields=['ws_tunnel_ports', 'updated_at'])

    sync = sync_workspace_tunnel_to_cluster(ws, respawn=True)
    payload = tunnel_info_payload(ws)
    payload['sync'] = sync

    if not sync.get('ok'):
        return JsonResponse({
            'message': sync.get('error') or 'ports saved but cluster sync failed',
            'result': payload,
        }, status=200)

    return JsonResponse({
        'message': sync.get('message') or ('Tunnel ports exposed' if ports else 'Tunnel ports cleared'),
        'result': payload,
    })
