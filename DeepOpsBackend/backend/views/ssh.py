import json

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from backend.models import Workspace
from backend.services.github_auth import auth
from backend.services.ssh_keys import create_or_rotate_keys, decrypt_private_key, get_or_none, ssh_info_payload
from backend.services.ssh_k8s import sync_workspace_ssh_to_cluster
from backend.views.workspaces import _get_workspace_for_user, _parse_body, _require_accepted


def _normalize_exec_shell(value) -> str:
    shell = str(value or Workspace.EXEC_SHELL_BASH).strip().lower()
    return shell if shell in (Workspace.EXEC_SHELL_BASH, Workspace.EXEC_SHELL_SH) else Workspace.EXEC_SHELL_BASH


@auth.verify
@require_http_methods(['GET'])
def workspace_ssh_info(request, user, workspace_id):
    denied = _require_accepted(user)
    if denied:
        return denied
    ws, err = _get_workspace_for_user(user, workspace_id)
    if err:
        return err
    return JsonResponse({'result': ssh_info_payload(ws)})


@auth.verify
@csrf_exempt
@require_http_methods(['POST'])
def workspace_ssh_generate(request, user, workspace_id):
    denied = _require_accepted(user)
    if denied:
        return denied
    ws, err = _get_workspace_for_user(user, workspace_id)
    if err:
        return err

    try:
        data = _parse_body(request)
    except json.JSONDecodeError:
        return JsonResponse({'message': 'invalid json'}, status=400)

    if 'exec_shell' in data:
        ws.exec_shell = _normalize_exec_shell(data.get('exec_shell'))
        ws.save(update_fields=['exec_shell', 'updated_at'])

    record, private_key = create_or_rotate_keys(ws)
    sync = sync_workspace_ssh_to_cluster(ws, public_key=record.public_key, respawn=True)

    payload = ssh_info_payload(ws)
    payload['private_key'] = private_key
    payload['sync'] = sync
    if not sync.get('ok'):
        return JsonResponse({
            'message': sync.get('error') or 'keys saved but SSH bridge sync failed',
            'result': payload,
        }, status=200)
    return JsonResponse({'result': payload})


@auth.verify
@require_http_methods(['GET'])
def workspace_ssh_download_key(request, user, workspace_id):
    denied = _require_accepted(user)
    if denied:
        return denied
    ws, err = _get_workspace_for_user(user, workspace_id)
    if err:
        return err
    record = get_or_none(ws)
    if not record:
        return JsonResponse({'message': 'no ssh key'}, status=404)
    private_key = decrypt_private_key(record.private_key_encrypted)
    filename = f'dohub-{ws.slug}-id_ed25519'
    response = HttpResponse(private_key, content_type='application/x-pem-file')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
