"""SSH node manager key, health checks, and interactive sessions."""

from __future__ import annotations

import json
import shlex
import socket
import threading
import time
from io import StringIO
from typing import Callable, Iterable

import paramiko
from django.utils import timezone as dj_timezone

from backend.models import SSHNode, SSHNodeManagerKey

from .ssh_nodes_crypto import decrypt_private_key, encrypt_private_key, generate_keypair

# Run via bash: zsh misparses nested "..." / $(...) / awk "$5" in a plain -c string.
_HEALTH_SCRIPT = (
    'echo "$(hostname) | '
    "Load: $(cut -d' ' -f1-3 /proc/loadavg) | "
    "Mem: $(free -m | awk '/Mem:/ {printf \"%d/%dMB\", $3,$2}') | "
    "Disk: $(df -h / | awk 'NR==2 {print $5}')\""
)
HEALTH_COMMAND = 'bash -lc ' + shlex.quote(_HEALTH_SCRIPT)

CONNECT_TIMEOUT = 20
HEALTH_TIMEOUT = 25


def get_manager_key() -> SSHNodeManagerKey | None:
    return SSHNodeManagerKey.objects.filter(id=1).first()


def ensure_manager_key() -> SSHNodeManagerKey:
    record = get_manager_key()
    if record:
        return record
    return regenerate_manager_key()


def regenerate_manager_key() -> SSHNodeManagerKey:
    public_key, private_key, fingerprint = generate_keypair()
    record, _ = SSHNodeManagerKey.objects.update_or_create(
        id=1,
        defaults={
            'public_key': public_key.strip(),
            'encrypted_private_key': encrypt_private_key(private_key),
            'fingerprint': fingerprint,
        },
    )
    return record


def manager_private_key() -> str:
    record = ensure_manager_key()
    return decrypt_private_key(record.encrypted_private_key)


def _load_pkey(private_key: str) -> paramiko.PKey:
    return paramiko.Ed25519Key.from_private_key(StringIO(private_key))


def _connect(node: SSHNode, private_key: str) -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=node.host,
        port=node.port or 22,
        username=node.username,
        pkey=_load_pkey(private_key),
        timeout=CONNECT_TIMEOUT,
        banner_timeout=CONNECT_TIMEOUT,
        auth_timeout=CONNECT_TIMEOUT,
        look_for_keys=False,
        allow_agent=False,
    )
    return client


def check_node_health(node: SSHNode, *, save: bool = True) -> SSHNode:
    """Run the health probe over SSH and update node status fields."""
    node.status = SSHNode.STATUS_CHECKING
    if save:
        node.save(update_fields=['status', 'updated_at'])

    private_key = manager_private_key()
    try:
        client = _connect(node, private_key)
    except (paramiko.SSHException, socket.error, OSError) as exc:
        node.status = SSHNode.STATUS_OFFLINE
        node.health_line = ''
        node.last_error = str(exc)
        node.last_checked_at = dj_timezone.now()
        if save:
            node.save(update_fields=['status', 'health_line', 'last_error', 'last_checked_at', 'updated_at'])
        return node

    try:
        _stdin, stdout, stderr = client.exec_command(HEALTH_COMMAND, timeout=HEALTH_TIMEOUT)
        exit_code = stdout.channel.recv_exit_status()
        out = (stdout.read() or b'').decode('utf-8', errors='replace').strip()
        err = (stderr.read() or b'').decode('utf-8', errors='replace').strip()
        if exit_code != 0:
            raise RuntimeError(err or out or f'health command exited {exit_code}')
        node.status = SSHNode.STATUS_ONLINE
        node.health_line = out
        node.last_error = ''
    except (paramiko.SSHException, socket.error, OSError, RuntimeError, TimeoutError) as exc:
        node.status = SSHNode.STATUS_OFFLINE
        node.health_line = ''
        node.last_error = str(exc)
    finally:
        client.close()

    node.last_checked_at = dj_timezone.now()
    if save:
        node.save(update_fields=['status', 'health_line', 'last_error', 'last_checked_at', 'updated_at'])
    return node


def refresh_nodes(nodes: Iterable[SSHNode]) -> list[SSHNode]:
    updated: list[SSHNode] = []
    for node in nodes:
        updated.append(check_node_health(node))
    return updated


def open_shell_channel(node: SSHNode, *, cols: int = 80, rows: int = 24) -> tuple[paramiko.SSHClient, paramiko.Channel]:
    client = _connect(node, manager_private_key())
    channel = client.invoke_shell(term='xterm-256color', width=cols, height=rows)
    channel.settimeout(0.0)
    return client, channel


def bridge_ssh_channel(channel: paramiko.Channel, on_output: Callable[[bytes], None], on_close: Callable[[], None]) -> threading.Thread:
    """Read SSH channel in a background thread and forward bytes to on_output."""

    def _reader() -> None:
        try:
            while True:
                if channel.recv_ready():
                    data = channel.recv(4096)
                    if not data:
                        break
                    on_output(data)
                elif channel.exit_status_ready() or channel.closed:
                    break
                else:
                    time.sleep(0.02)
        finally:
            on_close()

    thread = threading.Thread(target=_reader, daemon=True)
    thread.start()
    return thread


def parse_client_message(raw: str) -> dict:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {'t': 'i', 'd': raw}
    if not isinstance(payload, dict):
        return {'t': 'i', 'd': raw}
    return payload


def apply_client_message(channel: paramiko.Channel, payload: dict) -> None:
    kind = payload.get('t')
    if kind == 'r':
        cols = max(int(payload.get('c', 80)), 1)
        rows = max(int(payload.get('r', 24)), 1)
        channel.resize_pty(width=cols, height=rows)
        return
    if kind == 'i':
        data = payload.get('d', '')
        if data:
            channel.send(data)
