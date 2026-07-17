from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from backend.models import User
from backend.services.github_auth import auth


@auth.verify
@require_http_methods(['GET'])
def users_search(request, user):
    """
    Lightweight user search for features like workspace collaborators.
    Returns accepted, non-admin users that match query (username/email).
    """
    if user is None or not getattr(user, 'is_accept', False):
        return JsonResponse({'message': 'no permission'}, status=403)

    q = (request.GET.get('q') or '').strip()
    if len(q) < 1:
        return JsonResponse({'result': []})

    qs = User.objects.filter(is_accept=True).exclude(role=User.ROLE_ADMIN)
    qs = qs.filter(Q(username__icontains=q) | Q(email__icontains=q))
    results = []
    for target in qs.order_by('username')[:20]:
        results.append({
            'id': target.id,
            'username': target.username,
            'email': target.email or '',
            'image': target.image or '',
        })
    return JsonResponse({'result': results})

