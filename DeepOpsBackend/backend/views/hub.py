import time

from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from backend.models import ResourceGroupMember, User, Workspace
from backend.services.github_auth import auth
from backend.services.k8s import remove_codehub
from backend.services.resource_limits import resource_limits_for_user


def _user_payload(user: User) -> dict:
    group_name = ''
    try:
        group_name = user.resource_group_membership.group.name
    except ResourceGroupMember.DoesNotExist:
        pass
    return {
        'id': user.id,
        'username': user.username,
        'email': user.email or '',
        'image': user.image,
        'last_activity': user.last_activity,
        'role': user.role,
        'is_accept': user.is_accept,
        'group_name': group_name,
    }


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


@auth.handle_callback
def github_callback(request, github_user):
    user = auth.register_or_update_user(github_user)
    return auth.login_user(user, request)


@auth.verify
def login(request, user):
    if user is None:
        return auth.oauth_login(request)
    return HttpResponseRedirect('/')


@auth.verify
def logout(request, user):
    return auth.logout_user(request)


@auth.verify
def index(request, user):
    return render(request, 'index.html', {
        'user': user,
        'is_login': bool(user),
    })


def page_error(request, code, error):
    return render(request, 'page-error.html', {'code': code, 'error': error}, status=code)


@auth.verify
@require_http_methods(['GET'])
def user_state(request, user):
    denied = _require_user(user)
    if denied:
        return denied
    payload = _user_payload(user)
    payload['resource_limits'] = resource_limits_for_user(user)
    return JsonResponse({'result': payload})


@auth.verify
@require_http_methods(['GET'])
def all_users(request, user):
    denied = _require_admin(user)
    if denied:
        return denied

    page = max(1, int(request.GET.get('page', 1)))
    per_page = min(48, max(6, int(request.GET.get('per_page', 10))))
    user_filter = (request.GET.get('user') or '').strip()
    status = (request.GET.get('status') or '').strip().lower()

    qs = User.objects.select_related('resource_group_membership__group').order_by('username')
    if user_filter:
        qs = qs.filter(Q(username__icontains=user_filter) | Q(email__icontains=user_filter))
    if status == 'accepted':
        qs = qs.filter(is_accept=True)
    elif status == 'pending':
        qs = qs.filter(is_accept=False)

    paginator = Paginator(qs, per_page)
    page_obj = paginator.get_page(page)
    return JsonResponse({
        'result': [_user_payload(hub_user) for hub_user in page_obj.object_list],
        'pagination': {
            'page': page_obj.number,
            'per_page': per_page,
            'total': paginator.count,
            'pages': paginator.num_pages or 1,
        },
    })


@auth.verify
@require_http_methods(['GET', 'POST', 'PUT', 'DELETE'])
def accept_user(request, user, username):
    denied = _require_admin(user)
    if denied:
        return denied
    target = User.objects.filter(username=username).first()
    if not target:
        return JsonResponse({'message': 'not found'}, status=404)
    target.is_accept = True
    target.save(update_fields=['is_accept'])
    return JsonResponse({'message': 'success'})


def _stop_all_workspaces(target: User):
    from backend.services.k8s_status import live_workspace_state, workspace_is_active

    for ws in Workspace.objects.filter(user=target):
        if workspace_is_active(live_workspace_state(ws)):
            remove_codehub(ws.release_name)


@auth.verify
@csrf_exempt
@require_http_methods(['GET', 'POST', 'PUT', 'DELETE'])
def delete_user(request, user, username):
    denied = _require_admin(user)
    if denied:
        return denied
    target = User.objects.filter(username=username).first()
    if not target:
        return JsonResponse({'message': 'not found'}, status=404)
    try:
        _stop_all_workspaces(target)
    except Exception:
        return JsonResponse({'message': 'action failed'}, status=500)
    target.delete()
    return JsonResponse({'message': 'success'})


@auth.verify
@csrf_exempt
@require_http_methods(['GET', 'POST', 'PUT', 'DELETE'])
def change_role(request, user, username, role):
    denied = _require_admin(user)
    if denied:
        return denied
    if user.username == username:
        return JsonResponse({'message': 'no permission'}, status=403)
    if not user.is_accept:
        return JsonResponse({'message': 'no permission'}, status=403)

    target = User.objects.filter(username=username).first()
    if not target or not target.is_accept:
        return JsonResponse({'message': 'no permission'}, status=403)
    if role not in (User.ROLE_ADMIN, User.ROLE_NORMAL):
        return JsonResponse({'message': 'no permission'}, status=403)

    target.role = role
    target.save(update_fields=['role'])
    return JsonResponse({'message': 'success'})


@auth.verify
def touch_activity(request, user):
    if user:
        user.last_activity = time.time() * 1000
        user.save(update_fields=['last_activity'])
    return JsonResponse({'ok': True})
