#!/usr/bin/env python3
"""asyncssh SSH server (key auth only). Tunneled over HTTPS by wstunnel sidecar."""

from __future__ import annotations

import asyncio
import contextlib
import errno
import fcntl
import logging
import os
import re
import struct
import subprocess
import sys
import termios
from pathlib import Path

import asyncssh

LOG = logging.getLogger('ssh_bridge')
BUILD_ID = 'ssh-bridge-2026-06-11-pty-close'

SSH_BIND_HOST = os.environ.get('SSH_BIND_HOST', '127.0.0.1')
SSH_PORT = int(os.environ.get('SSH_PORT', '2222'))
AUTHORIZED_KEYS = Path(os.environ.get('AUTHORIZED_KEYS', '/ssh/authorized_keys'))
HOST_KEY = Path(os.environ.get('HOST_KEY', '/ssh-data/host_key'))
SSH_USER = os.environ.get('SSH_USER', 'coder')
POD_NAME = os.environ.get('POD_NAME', '')
POD_NAMESPACE = os.environ.get('POD_NAMESPACE', '')
TARGET_CONTAINER = os.environ.get('TARGET_CONTAINER', 'codehub')
READ_CHUNK = 65536
SESSION_MARKER = b'___DOHUB_SSH_EOF___'
LOGOUT_RE = re.compile(br'logout\r?\n')
# Remote bash prints "logout" on exit; trap marker is a fallback if stream stalls.
REMOTE_SHELL = (
    'stty -echoctl 2>/dev/null; '
    'trap \'printf "\\n___DOHUB_SSH_EOF___\\n"\' EXIT; '
    'exec bash -l'
)


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


def _set_pty_winsize(fd: int, rows: int, cols: int) -> None:
    rows = max(rows, 1)
    cols = max(cols, 1)
    winsize = struct.pack('HHHH', rows, cols, 0, 0)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)


def _term_cols_rows(process: asyncssh.SSHServerProcess) -> tuple[int, int]:
    size = process.term_size
    if size:
        return max(size[0], 1), max(size[1], 1)
    return 80, 24


def _shell_env(process: asyncssh.SSHServerProcess, cols: int, rows: int) -> dict[str, str]:
    env = os.environ.copy()
    if process.term_type:
        env['TERM'] = process.term_type
    env['COLUMNS'] = str(cols)
    env['LINES'] = str(rows)
    return env


def _attach_terminal_resize(process: asyncssh.SSHServerProcess, master_fd: int) -> None:
    """Forward SSH client window resizes to the local kubectl exec PTY."""

    def terminal_size_changed(width: int, height: int, pixwidth: int, pixheight: int) -> None:
        del pixwidth, pixheight
        try:
            _set_pty_winsize(master_fd, height, width)
        except OSError:
            LOG.debug('pty resize failed', exc_info=True)

    process.terminal_size_changed = terminal_size_changed


def _set_nonblocking(fd: int) -> None:
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)


def _close_pty_master(fd: int) -> None:
    """Close a PTY master fd. PTYs do not support os.shutdown() (Linux EINVAL)."""
    if fd < 0:
        return
    with contextlib.suppress(OSError):
        os.close(fd)


def _stop_shell(shell: subprocess.Popen[bytes]) -> int:
    if shell.poll() is not None:
        return shell.returncode or 0
    shell.terminate()
    try:
        return shell.wait(timeout=3) or 0
    except subprocess.TimeoutExpired:
        shell.kill()
        return shell.wait(timeout=1) or 0


def _session_should_end(tail: bytes) -> bool:
    if SESSION_MARKER in tail:
        return True
    return LOGOUT_RE.search(tail) is not None


def _strip_session_marker(data: bytes) -> bytes:
    if SESSION_MARKER not in data:
        return data
    return data.replace(SESSION_MARKER + b'\n', b'').replace(SESSION_MARKER, b'')


async def _run_command(process: asyncssh.SSHServerProcess) -> int:
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
    code = await proc.wait()
    return code if code is not None else 0


async def _forward_ssh_to_pty(
    process: asyncssh.SSHServerProcess,
    master_fd: int,
    stop_event: asyncio.Event,
) -> None:
    try:
        while not stop_event.is_set():
            data = await process.stdin.read(READ_CHUNK)
            if not data:
                stop_event.set()
                break
            await asyncio.get_running_loop().run_in_executor(None, os.write, master_fd, data)
    except (asyncssh.DisconnectError, BrokenPipeError, OSError):
        stop_event.set()


async def _forward_pty_to_ssh(
    process: asyncssh.SSHServerProcess,
    master_fd: int,
    stop_event: asyncio.Event,
) -> None:
    tail = b''
    loop = asyncio.get_running_loop()
    try:
        while not stop_event.is_set():
            try:
                data = await loop.run_in_executor(None, os.read, master_fd, READ_CHUNK)
            except OSError as exc:
                if exc.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
                    await asyncio.sleep(0.05)
                    continue
                stop_event.set()
                break
            if not data:
                LOG.info('pty read EOF')
                stop_event.set()
                break
            tail = (tail + data)[-512:]
            out = _strip_session_marker(data)
            if out:
                process.stdout.write(out)
            if _session_should_end(tail):
                LOG.info('remote shell exit detected (logout/marker)')
                stop_event.set()
                break
    except (asyncssh.DisconnectError, BrokenPipeError, OSError):
        stop_event.set()


async def _run_interactive_shell(process: asyncssh.SSHServerProcess) -> int:
    """Attach an interactive session to kubectl exec via a local PTY."""
    cols, rows = _term_cols_rows(process)
    master_fd, slave_fd = os.openpty()
    _set_pty_winsize(master_fd, rows, cols)
    _attach_terminal_resize(process, master_fd)
    _set_nonblocking(master_fd)
    env = _shell_env(process, cols, rows)
    stop_event = asyncio.Event()

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
            '-lc',
            REMOTE_SHELL,
        ],
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        env=env,
        preexec_fn=os.setsid,
    )
    os.close(slave_fd)

    to_pty = asyncio.create_task(_forward_ssh_to_pty(process, master_fd, stop_event))
    from_pty = asyncio.create_task(_forward_pty_to_ssh(process, master_fd, stop_event))
    shell_task = asyncio.create_task(asyncio.to_thread(shell.wait))

    code = 0
    try:
        wait_stop = asyncio.create_task(stop_event.wait())
        done, _pending = await asyncio.wait(
            {from_pty, to_pty, shell_task, wait_stop},
            return_when=asyncio.FIRST_COMPLETED,
        )

        if shell_task in done:
            code = shell_task.result() or 0
            LOG.info('kubectl exec exited code=%s', code)
        elif wait_stop in done or from_pty in done:
            LOG.info('closing SSH session after shell exit')
            code = _stop_shell(shell)
        else:
            LOG.info('SSH client disconnected')
            code = _stop_shell(shell)

        stop_event.set()
    finally:
        for task in (to_pty, from_pty):
            if not task.done():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
        if not shell_task.done():
            shell_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await shell_task
        _close_pty_master(master_fd)
        master_fd = -1
        if shell.poll() is None:
            with contextlib.suppress(subprocess.TimeoutExpired):
                shell.kill()
                shell.wait(timeout=1)

    return code


async def handle_client(process: asyncssh.SSHServerProcess) -> None:
    """Attach each SSH session to the workspace container via kubectl exec."""
    code = 1
    try:
        if process.command:
            code = await _run_command(process)
        else:
            code = await _run_interactive_shell(process)
    except Exception:
        LOG.exception('shell session failed')
        code = 1
    finally:
        with contextlib.suppress(Exception):
            await process.stdout.drain()
        LOG.info('SSH session closing exit=%s build=%s', code, BUILD_ID)
        process.exit(code & 0xFF)


async def ensure_host_key() -> None:
    if HOST_KEY.is_file():
        LOG.info('using SSH host key from %s', HOST_KEY)
        return
    HOST_KEY.parent.mkdir(parents=True, exist_ok=True)
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
