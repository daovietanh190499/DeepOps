"""
Asgi config for DeepOpsBackend project.

It exposes the Asgi callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DeepOpsBackend.settings')

application = get_asgi_application()