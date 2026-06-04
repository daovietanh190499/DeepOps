from functools import wraps
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.urls import reverse

from backend.models import User


class GitHubAuth:
    BASE_URL = 'https://api.github.com/'
    BASE_AUTH_URL = 'https://github.com/login/oauth/'

    def __init__(self):
        self.client_id = settings.GITHUB_CLIENT_ID
        self.client_secret = settings.GITHUB_CLIENT_SECRET
        self.admin_users = settings.ADMIN_USERS

    def oauth_login(self, request):
        params = urlencode({
            'client_id': self.client_id,
            'scope': 'read:user',
            'state': 'dohub',
            'allow_signup': 'true',
        })
        return HttpResponseRedirect(f'{self.BASE_AUTH_URL}authorize?{params}')

    def handle_callback(self, view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            code = request.GET.get('code')
            if not code:
                return HttpResponseForbidden('No permission')

            payload = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'code': code,
                'state': 'dohub',
            }
            token_resp = requests.post(
                f'{self.BASE_AUTH_URL}access_token',
                json=payload,
                headers={'Accept': 'application/json'},
                timeout=30,
            )
            token_data = token_resp.json()
            if 'access_token' not in token_data:
                return HttpResponseForbidden('No permission')

            access_token = token_data['access_token']
            user_resp = requests.get(
                f'{self.BASE_URL}user',
                headers={'Authorization': f'token {access_token}'},
                timeout=30,
            )
            user = user_resp.json()
            user['access_token'] = access_token
            return view_func(request, user, *args, **kwargs)

        return wrapper

    def verify(self, view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            access_key = request.COOKIES.get('user_access_key')
            user = None
            if access_key:
                user = User.objects.filter(access_key=access_key).first()
            return view_func(request, user, *args, **kwargs)

        return wrapper

    def login_user(self, user: User, request):
        user.issue_access_key()
        response = HttpResponseRedirect(reverse('index'))
        response.set_cookie('user_access_key', user.access_key, httponly=True, samesite='Lax')
        return response

    def logout_user(self, request):
        response = HttpResponseRedirect(reverse('index'))
        response.delete_cookie('user_access_key')
        return response

    def register_or_update_user(self, github_user: dict) -> User:
        username = github_user['login']
        is_admin = username in self.admin_users
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'image': github_user.get('avatar_url', ''),
                'role': User.ROLE_ADMIN if is_admin else User.ROLE_NORMAL,
                'is_accept': is_admin,
            },
        )
        user.github_access_token = github_user['access_token']
        user.github_id = int(github_user['id'])
        user.image = github_user.get('avatar_url', user.image)
        user.save()
        return user


auth = GitHubAuth()
