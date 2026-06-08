import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from backend.models import PlatformEquipmentOption, ServerPlanTemplate, User
from backend.services.github_auth import auth
from backend.services.platform_catalog import _template_payload, admin_catalog_payload, catalog_payload


def _require_admin(user):
    if user is None:
        return JsonResponse({'message': 'no permission'}, status=403)
    if user.role != User.ROLE_ADMIN:
        return JsonResponse({'message': 'no permission'}, status=403)
    return None


def _require_accepted(user):
    if user is None:
        return JsonResponse({'message': 'no permission'}, status=403)
    if not user.is_accept:
        return JsonResponse({'message': 'no permission'}, status=403)
    return None


def _parse_body(request) -> dict:
    if not request.body:
        return {}
    return json.loads(request.body.decode('utf-8'))


def _parse_exposed_ports(raw) -> list[int]:
    if isinstance(raw, list):
        ports = []
        for item in raw:
            try:
                port = int(item)
            except (TypeError, ValueError):
                continue
            if port > 0:
                ports.append(port)
        return ports or [8080]
    if isinstance(raw, str) and raw.strip():
        ports = []
        for part in raw.replace(';', ',').split(','):
            try:
                port = int(part.strip())
            except ValueError:
                continue
            if port > 0:
                ports.append(port)
        return ports or [8080]
    return [8080]


def _parse_container_command(raw) -> list[str]:
    if isinstance(raw, list):
        return [str(c).strip() for c in raw if str(c).strip()]
    if isinstance(raw, str):
        return [c for c in raw.split() if c]
    return []


@auth.verify
@require_http_methods(['GET'])
def platform_catalog(request, user):
    denied = _require_accepted(user)
    if denied:
        return denied
    return JsonResponse({'result': catalog_payload(active_only=True)})


@auth.verify
@require_http_methods(['GET'])
def admin_platform_catalog(request, user):
    denied = _require_admin(user)
    if denied:
        return denied
    return JsonResponse({'result': admin_catalog_payload()})


@auth.verify
@csrf_exempt
@require_http_methods(['POST'])
def admin_platform_option_create(request, user):
    denied = _require_admin(user)
    if denied:
        return denied
    try:
        data = _parse_body(request)
    except json.JSONDecodeError:
        return JsonResponse({'message': 'invalid json'}, status=400)

    category = (data.get('category') or '').strip()
    value = (data.get('value') or '').strip()
    if category not in dict(PlatformEquipmentOption.CATEGORY_CHOICES):
        return JsonResponse({'message': 'invalid category'}, status=400)
    if not value:
        return JsonResponse({'message': 'value required'}, status=400)
    if PlatformEquipmentOption.objects.filter(category=category, value=value).exists():
        return JsonResponse({'message': 'option already exists'}, status=400)

    option = PlatformEquipmentOption.objects.create(
        category=category,
        value=value,
        vram_g=int(data.get('vram_g', 0) or 0),
        sort_order=int(data.get('sort_order', 0) or 0),
        is_active=data.get('is_active', True),
    )
    return JsonResponse({'result': {'id': option.id}}, status=201)


@auth.verify
@csrf_exempt
@require_http_methods(['PUT', 'PATCH', 'DELETE'])
def admin_platform_option_detail(request, user, option_id):
    denied = _require_admin(user)
    if denied:
        return denied
    option = PlatformEquipmentOption.objects.filter(id=option_id).first()
    if not option:
        return JsonResponse({'message': 'not found'}, status=404)
    if request.method == 'DELETE':
        option.delete()
        return JsonResponse({'message': 'success'})

    try:
        data = _parse_body(request)
    except json.JSONDecodeError:
        return JsonResponse({'message': 'invalid json'}, status=400)

    if 'value' in data and data['value']:
        new_value = str(data['value']).strip()
        if PlatformEquipmentOption.objects.filter(
            category=option.category,
            value=new_value,
        ).exclude(id=option.id).exists():
            return JsonResponse({'message': 'option already exists'}, status=400)
        option.value = new_value
    if 'vram_g' in data:
        option.vram_g = int(data['vram_g'] or 0)
    if 'sort_order' in data:
        option.sort_order = int(data['sort_order'] or 0)
    if 'is_active' in data:
        option.is_active = bool(data['is_active'])
    option.save()
    return JsonResponse({'message': 'success'})


@auth.verify
@csrf_exempt
@require_http_methods(['POST'])
def admin_platform_template_create(request, user):
    denied = _require_admin(user)
    if denied:
        return denied
    try:
        data = _parse_body(request)
    except json.JSONDecodeError:
        return JsonResponse({'message': 'invalid json'}, status=400)

    name = (data.get('name') or '').strip()
    if not name:
        return JsonResponse({'message': 'name required'}, status=400)
    if ServerPlanTemplate.objects.filter(name=name).exists():
        return JsonResponse({'message': 'template already exists'}, status=400)

    template = ServerPlanTemplate.objects.create(
        name=name,
        image=(data.get('image') or 'logo.png').strip(),
        cpu=int(data.get('cpu', 2) or 2),
        ram=(data.get('ram') or '4G').strip(),
        gpu=(data.get('gpu') or 'none').strip() or 'none',
        docker_repository=(data.get('docker_repository') or '').strip(),
        docker_tag=(data.get('docker_tag') or '').strip(),
        exposed_ports=_parse_exposed_ports(data.get('exposed_ports')),
        container_command=_parse_container_command(
            data.get('container_command', data.get('command_text', data.get('command'))),
        ),
        env_defaults=data.get('env_defaults') if isinstance(data.get('env_defaults'), dict) else {},
        sort_order=int(data.get('sort_order', 0) or 0),
        is_active=data.get('is_active', True),
    )
    return JsonResponse({'result': {'id': template.id}}, status=201)


@auth.verify
@csrf_exempt
@require_http_methods(['PUT', 'PATCH', 'DELETE'])
def admin_platform_template_detail(request, user, template_id):
    denied = _require_admin(user)
    if denied:
        return denied
    template = ServerPlanTemplate.objects.filter(id=template_id).first()
    if not template:
        return JsonResponse({'message': 'not found'}, status=404)
    if request.method == 'DELETE':
        template.delete()
        return JsonResponse({'message': 'success'})

    try:
        data = _parse_body(request)
    except json.JSONDecodeError:
        return JsonResponse({'message': 'invalid json'}, status=400)

    if 'name' in data and data['name']:
        new_name = str(data['name']).strip()
        if ServerPlanTemplate.objects.filter(name=new_name).exclude(id=template.id).exists():
            return JsonResponse({'message': 'template already exists'}, status=400)
        template.name = new_name
    for field in ('image', 'ram', 'gpu', 'docker_repository', 'docker_tag'):
        if field in data and data[field] is not None:
            setattr(template, field, str(data[field]).strip())
    if 'cpu' in data:
        template.cpu = int(data['cpu'] or 2)
    if 'exposed_ports' in data:
        template.exposed_ports = _parse_exposed_ports(data['exposed_ports'])
    if any(key in data for key in ('container_command', 'command_text', 'command')):
        template.container_command = _parse_container_command(
            data.get('container_command', data.get('command_text', data.get('command'))),
        )
    if 'env_defaults' in data and isinstance(data['env_defaults'], dict):
        template.env_defaults = data['env_defaults']
    if 'sort_order' in data:
        template.sort_order = int(data['sort_order'] or 0)
    if 'is_active' in data:
        template.is_active = bool(data['is_active'])
    template.save()
    return JsonResponse({'result': _template_payload(template)})
