"""ASGI entrypoint with WebSocket routing for SSH node terminals."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DeepOpsBackend.settings')

django_asgi_app = get_asgi_application()

from backend.ws.ssh_node_terminal import websocket_application  # noqa: E402


async def application(scope, receive, send):
    if scope['type'] == 'websocket':
        await websocket_application(scope, receive, send)
        return
    await django_asgi_app(scope, receive, send)
