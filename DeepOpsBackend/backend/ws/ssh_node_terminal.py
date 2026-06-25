"""WebSocket bridge from browser xterm.js to managed SSH nodes."""

from __future__ import annotations

import asyncio
import uuid
from urllib.parse import parse_qs, unquote

from asgiref.sync import sync_to_async
from django.http import parse_cookie

from backend.models import SSHNode, User
from backend.services.ssh_nodes import (
    apply_client_message,
    bridge_ssh_channel,
    open_shell_channel,
    parse_client_message,
)


def _header_value(scope, name: str) -> str:
    target = name.lower().encode('ascii')
    for key, value in scope.get('headers', []):
        if key.lower() == target:
            return value.decode('latin-1')
    return ''


async def _admin_from_scope(scope) -> User | None:
    cookie_header = _header_value(scope, 'cookie')
    cookies = parse_cookie(cookie_header)
    access_key = cookies.get('user_access_key')
    if not access_key:
        return None
    return await sync_to_async(User.objects.filter(access_key=access_key).first)()


def _parse_positive_int(value: str | None, default: int) -> int:
    try:
        return max(int(value), 1)
    except (TypeError, ValueError):
        return default


def _query_params(scope) -> dict[str, list[str]]:
    raw = scope.get('query_string', b'')
    if isinstance(raw, bytes):
        raw = raw.decode('utf-8', errors='replace')
    return parse_qs(raw)


def _parse_node_id(path: str) -> uuid.UUID | None:
    parts = [part for part in unquote(path).split('/') if part]
    try:
        idx = parts.index('ssh-nodes')
        return uuid.UUID(parts[idx + 1])
    except (ValueError, IndexError):
        return None


async def ssh_node_terminal(scope, receive, send) -> None:
    if scope['type'] != 'websocket':
        return

    user = await _admin_from_scope(scope)
    if not user or user.role != 'admin':
        await send({'type': 'websocket.close', 'code': 4403})
        return

    node_id = _parse_node_id(scope.get('path', ''))
    if not node_id:
        await send({'type': 'websocket.close', 'code': 4400})
        return

    node = await sync_to_async(SSHNode.objects.filter(id=node_id).first)()
    if not node:
        await send({'type': 'websocket.close', 'code': 4404})
        return

    await send({'type': 'websocket.accept'})

    query = _query_params(scope)
    init_cols = _parse_positive_int((query.get('cols') or [''])[0], 80)
    init_rows = _parse_positive_int((query.get('rows') or [''])[0], 24)

    loop = asyncio.get_running_loop()
    outbound: asyncio.Queue[bytes | None] = asyncio.Queue()
    client = None
    channel = None

    def _push_output(data: bytes) -> None:
        loop.call_soon_threadsafe(outbound.put_nowait, data)

    def _on_reader_close() -> None:
        loop.call_soon_threadsafe(outbound.put_nowait, None)

    try:
        client, channel = await sync_to_async(open_shell_channel)(
            node, cols=init_cols, rows=init_rows,
        )
        bridge_ssh_channel(channel, _push_output, _on_reader_close)

        async def _forward_output() -> None:
            while True:
                chunk = await outbound.get()
                if chunk is None:
                    break
                await send({'type': 'websocket.send', 'bytes': chunk})

        forward_task = asyncio.create_task(_forward_output())

        while True:
            message = await receive()
            msg_type = message.get('type')
            if msg_type == 'websocket.disconnect':
                break
            if msg_type != 'websocket.receive':
                continue
            if message.get('bytes') is not None:
                await sync_to_async(channel.send)(message['bytes'].decode('utf-8', errors='replace'))
                continue
            text = message.get('text')
            if text is None:
                continue
            payload = parse_client_message(text)
            await sync_to_async(apply_client_message)(channel, payload)

        forward_task.cancel()
        try:
            await forward_task
        except asyncio.CancelledError:
            pass
    except Exception as exc:
        try:
            await send({
                'type': 'websocket.send',
                'text': f'\r\n\x1b[31m[ssh error] {exc}\x1b[0m\r\n',
            })
        except Exception:
            pass
    finally:
        if channel is not None:
            try:
                channel.close()
            except Exception:
                pass
        if client is not None:
            try:
                client.close()
            except Exception:
                pass
        try:
            await send({'type': 'websocket.close'})
        except Exception:
            pass


async def websocket_application(scope, receive, send) -> None:
    path = scope.get('path', '')
    if path.startswith('/ws/admin/ssh-nodes/') and path.endswith('/terminal'):
        await ssh_node_terminal(scope, receive, send)
        return
    await send({'type': 'websocket.close', 'code': 4404})
