"""ASGI entrypoint with WebSocket routing for SSH node terminals."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DeepOpsBackend.settings')

django_asgi_app = get_asgi_application()

from backend.ws.ssh_node_terminal import ssh_node_terminal  # noqa: E402
from backend.ws.workspace_terminal import workspace_terminal  # noqa: E402


async def websocket_application(scope, receive, send):
    path = scope.get('path', '')
    if path.startswith('/ws/admin/ssh-nodes/') and path.endswith('/terminal'):
        await ssh_node_terminal(scope, receive, send)
        return
    if path.startswith('/ws/workspaces/') and path.endswith('/terminal'):
        await workspace_terminal(scope, receive, send)
        return
    await send({'type': 'websocket.close', 'code': 4404})


async def application(scope, receive, send):
    if scope['type'] == 'websocket':
        await websocket_application(scope, receive, send)
        return
    await django_asgi_app(scope, receive, send)
