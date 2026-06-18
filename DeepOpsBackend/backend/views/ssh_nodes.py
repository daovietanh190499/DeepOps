"""Admin API for SSH node inventory and manager key."""

from __future__ import annotations

import json
import re
import uuid

from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from backend.models import SSHNode
from backend.services.github_auth import auth
from backend.services.ssh_nodes import (
    check_node_health,
    ensure_manager_key,
    refresh_nodes,
    regenerate_manager_key,
)


def _require_user(user):
    if user is None:
        return JsonResponse({'message': 'no permission'}, status=403)
    return None


def _require_admin(user):
    denied = _require_user(user)
    if denied:
        return denied
    if user.role != 'admin':
        return JsonResponse({'message': 'admin only'}, status=403)
    return None


def _parse_body(request) -> dict:
    if not request.body:
        return {}
    return json.loads(request.body.decode('utf-8'))


def _valid_host(host: str) -> bool:
    text = (host or '').strip()
    if not text or len(text) > 255:
        return False
    if text.startswith('.'):
        return False
    return bool(re.match(r'^[A-Za-z0-9._:-]+$', text))


@auth.verify
@require_http_methods(['GET'])
def admin_ssh_node_key(request, user):
    denied = _require_admin(user)
    if denied:
        return denied
    record = ensure_manager_key()
    return JsonResponse({'result': record.to_dict()})


@auth.verify
@csrf_exempt
@require_http_methods(['POST'])
def admin_ssh_node_key_regenerate(request, user):
    denied = _require_admin(user)
    if denied:
        return denied
    record = regenerate_manager_key()
    return JsonResponse({'result': record.to_dict(), 'message': 'SSH manager key regenerated'})


@auth.verify
@require_http_methods(['GET'])
def admin_ssh_nodes(request, user):
    denied = _require_admin(user)
    if denied:
        return denied
    page = max(1, int(request.GET.get('page', 1)))
    per_page = min(48, max(1, int(request.GET.get('per_page', 12))))
    qs = SSHNode.objects.all().order_by('-updated_at')
    paginator = Paginator(qs, per_page)
    page_obj = paginator.get_page(page)
    return JsonResponse({
        'result': [node.to_dict() for node in page_obj.object_list],
        'pagination': {
            'page': page_obj.number,
            'pages': paginator.num_pages,
            'total': paginator.count,
            'per_page': per_page,
        },
    })


def _node_fields(data: dict) -> tuple[dict | None, str | None]:
    host = (data.get('host') or '').strip()
    username = (data.get('username') or '').strip()
    label = (data.get('label') or '').strip()
    try:
        port = int(data.get('port', 22))
    except (TypeError, ValueError):
        return None, 'port must be an integer'
    if not _valid_host(host):
        return None, 'invalid host'
    if not username or len(username) > 128:
        return None, 'username is required'
    if port < 1 or port > 65535:
        return None, 'port must be between 1 and 65535'
    return {
        'host': host,
        'port': port,
        'username': username,
        'label': label[:255],
    }, None


@auth.verify
@csrf_exempt
@require_http_methods(['POST'])
def admin_ssh_node_create(request, user):
    denied = _require_admin(user)
    if denied:
        return denied
    try:
        data = _parse_body(request)
    except json.JSONDecodeError:
        return JsonResponse({'message': 'invalid json'}, status=400)
    fields, err = _node_fields(data)
    if err:
        return JsonResponse({'message': err}, status=400)
    ensure_manager_key()
    node = SSHNode.objects.create(**fields)
    check_node_health(node)
    return JsonResponse({'result': node.to_dict()})


@auth.verify
@csrf_exempt
@require_http_methods(['PUT', 'PATCH', 'DELETE'])
def admin_ssh_node_detail(request, user, node_id):
    denied = _require_admin(user)
    if denied:
        return denied
    try:
        node_uuid = uuid.UUID(str(node_id))
    except ValueError:
        return JsonResponse({'message': 'invalid node id'}, status=400)
    node = SSHNode.objects.filter(id=node_uuid).first()
    if not node:
        return JsonResponse({'message': 'not found'}, status=404)

    if request.method == 'DELETE':
        node.delete()
        return JsonResponse({'message': 'success'})

    try:
        data = _parse_body(request)
    except json.JSONDecodeError:
        return JsonResponse({'message': 'invalid json'}, status=400)
    merged = {
        'host': data.get('host', node.host),
        'port': data.get('port', node.port),
        'username': data.get('username', node.username),
        'label': data.get('label', node.label),
    }
    fields, err = _node_fields(merged)
    if err:
        return JsonResponse({'message': err}, status=400)
    for key, value in fields.items():
        setattr(node, key, value)
    node.save()
    return JsonResponse({'result': node.to_dict()})


@auth.verify
@csrf_exempt
@require_http_methods(['POST'])
def admin_ssh_nodes_refresh(request, user):
    denied = _require_admin(user)
    if denied:
        return denied
    try:
        data = _parse_body(request)
    except json.JSONDecodeError:
        return JsonResponse({'message': 'invalid json'}, status=400)
    ids = data.get('ids') or []
    if ids:
        uuids = []
        for raw in ids:
            try:
                uuids.append(uuid.UUID(str(raw)))
            except ValueError:
                continue
        nodes = list(SSHNode.objects.filter(id__in=uuids))
    else:
        nodes = list(SSHNode.objects.all())
    updated = refresh_nodes(nodes)
    return JsonResponse({'result': [node.to_dict() for node in updated]})


@auth.verify
@csrf_exempt
@require_http_methods(['POST'])
def admin_ssh_node_refresh(request, user, node_id):
    denied = _require_admin(user)
    if denied:
        return denied
    try:
        node_uuid = uuid.UUID(str(node_id))
    except ValueError:
        return JsonResponse({'message': 'invalid node id'}, status=400)
    node = SSHNode.objects.filter(id=node_uuid).first()
    if not node:
        return JsonResponse({'message': 'not found'}, status=404)
    check_node_health(node)
    return JsonResponse({'result': node.to_dict()})
