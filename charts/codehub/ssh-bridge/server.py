#!/usr/bin/env python3
"""asyncssh SSH server (key auth only). Tunneled over HTTPS by wstunnel sidecar."""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path

import asyncssh

LOG = logging.getLogger('ssh_bridge')
BUILD_ID = 'ssh-bridge-2026-06-06-kubectl-exec'

SSH_BIND_HOST = os.environ.get('SSH_BIND_HOST', '127.0.0.1')
SSH_PORT = int(os.environ.get('SSH_PORT', '2222'))
AUTHORIZED_KEYS = Path(os.environ.get('AUTHORIZED_KEYS', '/ssh/authorized_keys'))
HOST_KEY = Path(os.environ.get('HOST_KEY', '/ssh-data/host_key'))
SSH_USER = os.environ.get('SSH_USER', 'coder')
POD_NAME = os.environ.get('POD_NAME', '')
POD_NAMESPACE = os.environ.get('POD_NAMESPACE', '')
TARGET_CONTAINER = os.environ.get('TARGET_CONTAINER', 'codehub')


class DohubSSHServer(asyncssh.SSHServer):
    def begin_auth(self, username: str) -> bool:
        return username == SSH_USER

    def public_key_auth_supported(self) -> bool:
        return True

    async def validate_public_key(self, username: str, key) -> bool:
        if username != SSH_USER or not AUTHORIZED_KEYS.is_file():
            return False
        for line in AUTHORIZED_KEYS.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            try:
                allowed = asyncssh.import_public_key(line)
            except (asyncssh.KeyImportError, ValueError):
                continue
            if allowed == key:
                return True
        return False


def _kubectl_exec_base() -> list[str]:
    return [
        'kubectl',
        'exec',
        '-n',
        POD_NAMESPACE,
    ]


def _shell_env(process: asyncssh.SSHServerProcess) -> dict[str, str]:
    env = os.environ.copy()
    if process.term_type:
        env['TERM'] = process.term_type
    return env


async def _run_command(process: asyncssh.SSHServerProcess) -> int | None:
    proc = await asyncio.create_subprocess_exec(
        *_kubectl_exec_base(),
        POD_NAME,
        '-c',
        TARGET_CONTAINER,
        '--',
        '/bin/bash',
        '-lc',
        process.command,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await process.redirect(proc.stdin, proc.stdout, proc.stderr)
    await proc.wait()
    return proc.returncode


async def _run_interactive_shell(process: asyncssh.SSHServerProcess) -> int | None:
    master_fd, slave_fd = os.openpty()
    env = _shell_env(process)

    try:
        shell = subprocess.Popen(
            [
                *_kubectl_exec_base(),
                '-i',
                '-t',
                POD_NAME,
                '-c',
                TARGET_CONTAINER,
                '--',
                '/bin/bash',
                '-l',
            ],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            env=env,
            preexec_fn=os.setsid,
        )
    finally:
        os.close(slave_fd)

    await process.redirect(stdin=master_fd, stdout=os.dup(master_fd))
    await process.wait_closed()
    return shell.wait()


async def handle_client(process: asyncssh.SSHServerProcess) -> None:
    """Attach each SSH session to the workspace container via kubectl exec."""
    try:
        if process.command:
            code = await _run_command(process)
        else:
            code = await _run_interactive_shell(process)
        if code is not None:
            process.exit(code)
        else:
            process.close()
    except Exception:
        LOG.exception('shell session failed')
        process.exit(1)


async def ensure_host_key() -> None:
    HOST_KEY.parent.mkdir(parents=True, exist_ok=True)
    if HOST_KEY.exists():
        return
    key = asyncssh.generate_private_key('ssh-ed25519')
    key.write_private_key(str(HOST_KEY))
    LOG.info('generated ephemeral SSH host key at %s', HOST_KEY)


def _validate_kubectl_target() -> None:
    missing = [
        name
        for name, value in (
            ('POD_NAME', POD_NAME),
            ('POD_NAMESPACE', POD_NAMESPACE),
            ('TARGET_CONTAINER', TARGET_CONTAINER),
        )
        if not value
    ]
    if missing:
        LOG.error('missing required env for kubectl exec: %s', ', '.join(missing))
        sys.exit(1)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    _validate_kubectl_target()
    await ensure_host_key()
    await asyncssh.listen(
        SSH_BIND_HOST,
        SSH_PORT,
        server_factory=DohubSSHServer,
        process_factory=handle_client,
        server_host_keys=[str(HOST_KEY)],
        line_editor=False,
        encoding=None,
    )
    LOG.info(
        '%s asyncssh listening on %s:%s user=%s kubectl=%s/%s container=%s',
        BUILD_ID,
        SSH_BIND_HOST,
        SSH_PORT,
        SSH_USER,
        POD_NAMESPACE,
        POD_NAME,
        TARGET_CONTAINER,
    )
    await asyncio.Future()


if __name__ == '__main__':
    asyncio.run(main())
