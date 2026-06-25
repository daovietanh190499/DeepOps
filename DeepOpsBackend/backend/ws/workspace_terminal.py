"""WebSocket bridge from browser xterm.js to workspace main container via kubectl exec."""

from __future__ import annotations

import asyncio
import uuid
from urllib.parse import parse_qs, unquote

from asgiref.sync import sync_to_async
from django.http import parse_cookie

from backend.models import User, Workspace
from backend.services.workspace_terminal import (
    WorkspaceKubectlExecSession,
    normalize_exec_shell,
    parse_client_message,
    resolve_exec_target,
)


def _header_value(scope, name: str) -> str:
    target = name.lower().encode('ascii')
    for key, value in scope.get('headers', []):
        if key.lower() == target:
            return value.decode('latin-1')
    return ''


async def _user_from_scope(scope) -> User | None:
    cookie_header = _header_value(scope, 'cookie')
    cookies = parse_cookie(cookie_header)
    access_key = cookies.get('user_access_key')
    if not access_key:
        return None
    return await sync_to_async(User.objects.filter(access_key=access_key).first)()


def _parse_workspace_id(path: str) -> uuid.UUID | None:
    parts = [part for part in unquote(path).split('/') if part]
    try:
        idx = parts.index('workspaces')
        return uuid.UUID(parts[idx + 1])
    except (ValueError, IndexError):
        return None


def _query_params(scope) -> dict[str, list[str]]:
    raw = scope.get('query_string', b'')
    if isinstance(raw, bytes):
        raw = raw.decode('utf-8', errors='replace')
    return parse_qs(raw)


async def _workspace_for_user(user: User, workspace_id: uuid.UUID) -> Workspace | None:
    ws = await sync_to_async(
        Workspace.objects.filter(id=workspace_id).select_related('user').first,
    )()
    if not ws:
        return None
    if user.role != User.ROLE_ADMIN and ws.user_id != user.id:
        return None
    return ws


def _parse_positive_int(value: str | None, default: int) -> int:
    try:
        return max(int(value), 1)
    except (TypeError, ValueError):
        return default


async def workspace_terminal(scope, receive, send) -> None:
    if scope['type'] != 'websocket':
        return

    user = await _user_from_scope(scope)
    if not user or not user.is_accept:
        await send({'type': 'websocket.close', 'code': 4403})
        return

    workspace_id = _parse_workspace_id(scope.get('path', ''))
    if not workspace_id:
        await send({'type': 'websocket.close', 'code': 4400})
        return

    workspace = await _workspace_for_user(user, workspace_id)
    if not workspace:
        await send({'type': 'websocket.close', 'code': 4403})
        return

    query = _query_params(scope)
    shell = normalize_exec_shell((query.get('shell') or [''])[0])
    pod_name = (query.get('pod') or [''])[0].strip() or None
    init_cols = _parse_positive_int((query.get('cols') or [''])[0], 80)
    init_rows = _parse_positive_int((query.get('rows') or [''])[0], 24)

    try:
        pod, _container = await sync_to_async(resolve_exec_target)(
            workspace,
            pod_name=pod_name,
        )
    except RuntimeError as exc:
        await send({'type': 'websocket.accept'})
        await send({
            'type': 'websocket.send',
            'text': f'\r\n\x1b[31m[terminal] {exc}\x1b[0m\r\n',
        })
        await send({'type': 'websocket.close', 'code': 4404})
        return

    await send({'type': 'websocket.accept'})

    loop = asyncio.get_running_loop()
    outbound: asyncio.Queue[bytes | None] = asyncio.Queue()
    session: WorkspaceKubectlExecSession | None = None

    def _push_output(data: bytes) -> None:
        loop.call_soon_threadsafe(outbound.put_nowait, data)

    def _on_reader_close() -> None:
        loop.call_soon_threadsafe(outbound.put_nowait, None)

    try:
        session = await sync_to_async(WorkspaceKubectlExecSession)(
            pod, shell, cols=init_cols, rows=init_rows,
        )
        await sync_to_async(session.read_loop)(_push_output, _on_reader_close)

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
                await sync_to_async(session.write)(
                    message['bytes'],
                )
                continue
            text = message.get('text')
            if text is None:
                continue
            payload = parse_client_message(text)
            await sync_to_async(session.apply_client_message)(payload)

        forward_task.cancel()
        try:
            await forward_task
        except asyncio.CancelledError:
            pass
    except Exception as exc:
        try:
            await send({
                'type': 'websocket.send',
                'text': f'\r\n\x1b[31m[terminal error] {exc}\x1b[0m\r\n',
            })
        except Exception:
            pass
    finally:
        if session is not None:
            await sync_to_async(session.close)()
        try:
            await send({'type': 'websocket.close'})
        except Exception:
            pass
