"""Interactive kubectl exec into the workspace main container."""

from __future__ import annotations

import fcntl
import json
import os
import struct
import subprocess
import termios
import threading
import time
from typing import Callable

from backend.models import Workspace
from backend.services.k8s_env import NAMESPACE
from backend.services.k8s_status import workspace_pods_for_id

WORKSPACE_MAIN_CONTAINER = 'codehub'


def normalize_exec_shell(value: str | None) -> str:
    text = (value or Workspace.EXEC_SHELL_BASH).strip().lower()
    return Workspace.EXEC_SHELL_SH if text == 'sh' else Workspace.EXEC_SHELL_BASH


def resolve_exec_target(
    workspace: Workspace,
    *,
    pod_name: str | None = None,
) -> tuple[str, str]:
    pods = workspace_pods_for_id(str(workspace.id))
    if not pods:
        raise RuntimeError('No pods found. Start the server first.')
    selected = (pod_name or '').strip() or pods[0]['name']
    if not any(item['name'] == selected for item in pods):
        selected = pods[0]['name']
    return selected, WORKSPACE_MAIN_CONTAINER


def _set_pty_winsize(fd: int, rows: int, cols: int) -> None:
    winsize = struct.pack('HHHH', rows, cols, 0, 0)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)


def _shell_argv(shell: str) -> list[str]:
    if shell == Workspace.EXEC_SHELL_SH:
        return ['sh', '-c', 'exec sh']
    return ['bash', '-lc', 'exec bash -l']


def parse_client_message(raw: str) -> dict:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {'t': 'i', 'd': raw}
    if not isinstance(payload, dict):
        return {'t': 'i', 'd': raw}
    return payload


class WorkspaceKubectlExecSession:
    def __init__(
        self,
        pod: str,
        shell: str,
        *,
        cols: int = 80,
        rows: int = 24,
    ) -> None:
        self.pod = pod
        self.shell = normalize_exec_shell(shell)
        self.master_fd = -1
        self.process: subprocess.Popen | None = None
        self._open(cols, rows)

    def _open(self, cols: int, rows: int) -> None:
        master_fd, slave_fd = os.openpty()
        _set_pty_winsize(master_fd, rows, cols)
        env = os.environ.copy()
        env['TERM'] = 'xterm-256color'
        env['COLUMNS'] = str(cols)
        env['LINES'] = str(rows)
        self.process = subprocess.Popen(
            [
                'kubectl', 'exec',
                '-n', NAMESPACE,
                '-i', '-t',
                self.pod,
                '-c', WORKSPACE_MAIN_CONTAINER,
                '--',
                *_shell_argv(self.shell),
            ],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            env=env,
            preexec_fn=os.setsid,
        )
        os.close(slave_fd)
        self.master_fd = master_fd
        flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
        fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

    def write(self, data: bytes) -> None:
        if self.master_fd >= 0 and data:
            os.write(self.master_fd, data)

    def apply_client_message(self, payload: dict) -> None:
        kind = payload.get('t')
        if kind == 'r':
            cols = max(int(payload.get('c', 80)), 1)
            rows = max(int(payload.get('r', 24)), 1)
            self.resize(cols, rows)
            return
        if kind == 'i':
            text = payload.get('d', '')
            if text:
                self.write(text.encode('utf-8', errors='replace'))

    def resize(self, cols: int, rows: int) -> None:
        if self.master_fd >= 0:
            _set_pty_winsize(self.master_fd, rows, cols)

    def read_loop(
        self,
        on_output: Callable[[bytes], None],
        on_close: Callable[[], None],
    ) -> threading.Thread:
        def _reader() -> None:
            try:
                while True:
                    if self.process is not None and self.process.poll() is not None:
                        break
                    try:
                        data = os.read(self.master_fd, 4096)
                        if not data:
                            time.sleep(0.02)
                            if self.process is not None and self.process.poll() is not None:
                                break
                            continue
                        on_output(data)
                    except BlockingIOError:
                        if self.process is not None and self.process.poll() is not None:
                            break
                        time.sleep(0.02)
                    except OSError:
                        break
            finally:
                on_close()

        thread = threading.Thread(target=_reader, daemon=True)
        thread.start()
        return thread

    def close(self) -> None:
        if self.process is not None and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
        if self.master_fd >= 0:
            try:
                os.close(self.master_fd)
            except OSError:
                pass
            self.master_fd = -1
