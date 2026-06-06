import json
import re

from django.db.models import Count, Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from backend.models import ResourceGroup, ResourceGroupMember, User
from backend.services.github_auth import auth
from backend.services.resource_limits import allowed_equipment


def _require_admin(user):
    if user is None:
        return JsonResponse({'message': 'no permission'}, status=403)
    if user.role != User.ROLE_ADMIN:
        return JsonResponse({'message': 'no permission'}, status=403)
    return None


def _parse_body(request) -> dict:
    if not request.body:
        return {}
    return json.loads(request.body.decode('utf-8'))


def _member_payload(member: ResourceGroupMember) -> dict:
    return {
        'id': str(member.id),
        'user_id': member.user_id,
        'username': member.user.username,
        'email': member.user.email or '',
        'image': member.user.image,
    }


def _group_payload(group: ResourceGroup, *, include_members: bool = False) -> dict:
    member_count = getattr(group, 'member_count', None)
    if member_count is None:
        member_count = group.members.count()
    data = {
        'id': str(group.id),
        'name': group.name,
        'max_cpu': group.max_cpu,
        'max_ram_g': group.max_ram_g,
        'max_drive_size_gi': group.max_drive_size_gi,
        'max_gpu_vram_g': group.max_gpu_vram_g,
        'member_count': member_count,
        'equipment': allowed_equipment(group),
    }
    if include_members:
        members = group.members.select_related('user').order_by('user__username')
        data['members'] = [_member_payload(m) for m in members]
    return data


def _parse_group_fields(data: dict) -> tuple[dict | None, str | None]:
    try:
        fields = {
            'name': (data.get('name') or '').strip()[:128],
            'max_cpu': int(data.get('max_cpu', 0)),
            'max_ram_g': int(data.get('max_ram_g', 0)),
            'max_drive_size_gi': int(data.get('max_drive_size_gi', 0)),
            'max_gpu_vram_g': int(data.get('max_gpu_vram_g', 0)),
        }
    except (TypeError, ValueError):
        return None, 'invalid limit values'
    if not fields['name']:
        return None, 'name required'
    for key in ('max_cpu', 'max_ram_g', 'max_drive_size_gi'):
        if fields[key] <= 0:
            return None, f'{key} must be positive'
    if fields['max_gpu_vram_g'] < 0:
        return None, 'max_gpu_vram_g must be non-negative'
    return fields, None


def _parse_email_list(data: dict) -> list[str]:
    emails = data.get('emails')
    if isinstance(emails, list):
        raw = emails
    else:
        text = (data.get('emails_text') or data.get('text') or '').strip()
        if not text:
            return []
        raw = re.split(r'[\s,;]+', text)
    out = []
    seen = set()
    for item in raw:
        email = str(item).strip().lower()
        if not email or email in seen:
            continue
        seen.add(email)
        out.append(email)
    return out


@auth.verify
@require_http_methods(['GET'])
def admin_resource_groups(request, user):
    denied = _require_admin(user)
    if denied:
        return denied
    groups = (
        ResourceGroup.objects.annotate(member_count=Count('members'))
        .order_by('name')
    )
    return JsonResponse({'result': [_group_payload(g) for g in groups]})


@auth.verify
@csrf_exempt
@require_http_methods(['POST'])
def admin_resource_group_create(request, user):
    denied = _require_admin(user)
    if denied:
        return denied
    try:
        data = _parse_body(request)
    except json.JSONDecodeError:
        return JsonResponse({'message': 'invalid json'}, status=400)

    fields, err = _parse_group_fields(data)
    if err:
        return JsonResponse({'message': err}, status=400)
    if ResourceGroup.objects.filter(name=fields['name']).exists():
        return JsonResponse({'message': 'group name already exists'}, status=400)

    group = ResourceGroup.objects.create(**fields)
    return JsonResponse({'result': _group_payload(group)}, status=201)


@auth.verify
@require_http_methods(['GET'])
def admin_resource_group_detail(request, user, group_id):
    denied = _require_admin(user)
    if denied:
        return denied
    group = ResourceGroup.objects.filter(id=group_id).first()
    if not group:
        return JsonResponse({'message': 'not found'}, status=404)
    return JsonResponse({'result': _group_payload(group, include_members=True)})


@auth.verify
@csrf_exempt
@require_http_methods(['PUT', 'PATCH', 'DELETE'])
def admin_resource_group_update(request, user, group_id):
    denied = _require_admin(user)
    if denied:
        return denied
    group = ResourceGroup.objects.filter(id=group_id).first()
    if not group:
        return JsonResponse({'message': 'not found'}, status=404)

    if request.method == 'DELETE':
        group.delete()
        return JsonResponse({'message': 'success'})

    try:
        data = _parse_body(request)
    except json.JSONDecodeError:
        return JsonResponse({'message': 'invalid json'}, status=400)

    fields, err = _parse_group_fields(data)
    if err:
        return JsonResponse({'message': err}, status=400)
    if ResourceGroup.objects.filter(name=fields['name']).exclude(id=group.id).exists():
        return JsonResponse({'message': 'group name already exists'}, status=400)

    for key, value in fields.items():
        setattr(group, key, value)
    group.save()
    return JsonResponse({'result': _group_payload(group)})


@auth.verify
@require_http_methods(['GET'])
def admin_user_search(request, user):
    denied = _require_admin(user)
    if denied:
        return denied

    q = (request.GET.get('q') or '').strip()
    exclude_group = (request.GET.get('exclude_group') or '').strip()
    if len(q) < 1:
        return JsonResponse({'result': []})

    qs = User.objects.filter(is_accept=True).exclude(role=User.ROLE_ADMIN)
    qs = qs.filter(Q(username__icontains=q) | Q(email__icontains=q))
    if exclude_group:
        qs = qs.exclude(resource_group_membership__group_id=exclude_group)

    results = []
    for target in qs.order_by('username')[:20]:
        group_name = ''
        try:
            group_name = target.resource_group_membership.group.name
        except ResourceGroupMember.DoesNotExist:
            pass
        results.append({
            'id': target.id,
            'username': target.username,
            'email': target.email or '',
            'image': target.image,
            'group_name': group_name,
        })
    return JsonResponse({'result': results})


@auth.verify
@csrf_exempt
@require_http_methods(['POST'])
def admin_resource_group_add_member(request, user, group_id):
    denied = _require_admin(user)
    if denied:
        return denied
    group = ResourceGroup.objects.filter(id=group_id).first()
    if not group:
        return JsonResponse({'message': 'not found'}, status=404)

    try:
        data = _parse_body(request)
    except json.JSONDecodeError:
        return JsonResponse({'message': 'invalid json'}, status=400)

    user_id = data.get('user_id')
    if not user_id:
        return JsonResponse({'message': 'user_id required'}, status=400)

    target = User.objects.filter(id=user_id, is_accept=True).exclude(role=User.ROLE_ADMIN).first()
    if not target:
        return JsonResponse({'message': 'user not found'}, status=404)

    ResourceGroupMember.objects.filter(user=target).exclude(group=group).delete()
    member, created = ResourceGroupMember.objects.get_or_create(group=group, user=target)
    return JsonResponse({
        'message': 'success',
        'result': _member_payload(member),
        'created': created,
    }, status=201 if created else 200)


@auth.verify
@csrf_exempt
@require_http_methods(['DELETE'])
def admin_resource_group_remove_member(request, user, group_id, member_user_id):
    denied = _require_admin(user)
    if denied:
        return denied
    deleted, _ = ResourceGroupMember.objects.filter(
        group_id=group_id,
        user_id=member_user_id,
    ).delete()
    if not deleted:
        return JsonResponse({'message': 'not found'}, status=404)
    return JsonResponse({'message': 'success'})


@auth.verify
@csrf_exempt
@require_http_methods(['POST'])
def admin_resource_group_bulk_add_members(request, user, group_id):
    denied = _require_admin(user)
    if denied:
        return denied
    group = ResourceGroup.objects.filter(id=group_id).first()
    if not group:
        return JsonResponse({'message': 'not found'}, status=404)

    try:
        data = _parse_body(request)
    except json.JSONDecodeError:
        return JsonResponse({'message': 'invalid json'}, status=400)

    emails = _parse_email_list(data)
    if not emails:
        return JsonResponse({'message': 'emails required'}, status=400)

    results = []
    added = 0
    for email in emails:
        target = (
            User.objects.filter(is_accept=True)
            .exclude(role=User.ROLE_ADMIN)
            .filter(Q(email__iexact=email) | Q(username__iexact=email))
            .first()
        )
        if not target:
            results.append({'email': email, 'ok': False, 'error': 'user not found'})
            continue
        ResourceGroupMember.objects.filter(user=target).exclude(group=group).delete()
        member, created = ResourceGroupMember.objects.get_or_create(group=group, user=target)
        results.append({
            'email': email,
            'ok': True,
            'username': target.username,
            'created': created,
            'member_id': str(member.id),
        })
        if created:
            added += 1

    ok_count = sum(1 for r in results if r.get('ok'))
    return JsonResponse({
        'message': 'success',
        'added': added,
        'matched': ok_count,
        'failed': len(results) - ok_count,
        'results': results,
    })
