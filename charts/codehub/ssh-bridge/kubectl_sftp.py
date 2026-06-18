"""SFTP/SCP server backed by kubectl cp into the workspace container."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import posixpath
import secrets
import stat
import subprocess
from pathlib import Path

import asyncssh
from asyncssh.constants import FILEXFER_TYPE_DIRECTORY, FILEXFER_TYPE_REGULAR
from asyncssh.sftp import (
    FXF_APPEND,
    FXF_CREAT,
    FXF_EXCL,
    FXF_READ,
    FXF_TRUNC,
    FXF_WRITE,
    SFTPAttrs,
    SFTPFailure,
    SFTPNoSuchFile,
    SFTPPermissionDenied,
)

LOG = logging.getLogger('ssh_bridge')

POD_NAME = os.environ.get('POD_NAME', '')
POD_NAMESPACE = os.environ.get('POD_NAMESPACE', '')
TARGET_CONTAINER = os.environ.get('TARGET_CONTAINER', 'codehub')


def _shlex_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


class _KubectlFile:
    """Local staging file mapped to a path in the workspace container."""

    __slots__ = ('local_path', 'remote_path', 'upload_on_close', '_fp')

    def __init__(
        self,
        local_path: Path,
        remote_path: str,
        *,
        upload_on_close: bool,
        mode: str,
    ) -> None:
        self.local_path = local_path
        self.remote_path = remote_path
        self.upload_on_close = upload_on_close
        self.local_path.parent.mkdir(parents=True, exist_ok=True)
        self._fp = open(local_path, mode)

    def seek(self, offset: int) -> None:
        self._fp.seek(offset)

    def read(self, size: int) -> bytes:
        return self._fp.read(size)

    def write(self, data: bytes) -> int:
        return self._fp.write(data)

    def flush(self) -> None:
        self._fp.flush()

    def close(self) -> None:
        self._fp.close()


def _normalize_container_path(path: bytes) -> str:
    text = path.decode('utf-8', errors='surrogateescape')
    norm = posixpath.normpath(text)
    if not norm.startswith('/'):
        norm = '/' + norm
    parts = [part for part in norm.split('/') if part and part != '.']
    if '..' in parts:
        raise SFTPPermissionDenied('Path traversal is not allowed')
    return '/' + '/'.join(parts) if parts else '/'


def _kubectl_cp_from_container(remote_path: str, local_path: Path) -> tuple[int, str]:
    local_path.parent.mkdir(parents=True, exist_ok=True)
    source = f'{POD_NAMESPACE}/{POD_NAME}:{remote_path}'
    result = subprocess.run(
        [
            'kubectl', 'cp',
            source,
            str(local_path),
            '-n', POD_NAMESPACE,
            '-c', TARGET_CONTAINER,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    logs = ((result.stdout or '') + (result.stderr or '')).strip()
    return result.returncode, logs


def _kubectl_cp_to_container(local_path: Path, remote_path: str) -> tuple[int, str, str]:
    target = remote_path
    dest = f'{POD_NAMESPACE}/{POD_NAME}:{target}'
    result = subprocess.run(
        [
            'kubectl', 'cp',
            str(local_path),
            dest,
            '-n', POD_NAMESPACE,
            '-c', TARGET_CONTAINER,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    logs = ((result.stdout or '') + (result.stderr or '')).strip()
    return result.returncode, logs, target


def _kubectl_path_attrs(remote_path: str) -> SFTPAttrs:
    quoted = _shlex_quote(remote_path)
    # Keep exit status 0 once the path exists; OpenSSH scp treats STAT failure
    # as "not a directory" and uploads to the directory path as a file name.
    cmd = (
        f'if [ ! -e {quoted} ]; then exit 1; fi; '
        f'if [ -d {quoted} ]; then echo DIR; '
        f'elif [ -f {quoted} ]; then echo FILE; '
        f'else echo OTHER; fi; '
        f'stat -c "%s %Y" {quoted} 2>/dev/null || echo "0 $(date +%s)"'
    )
    result = subprocess.run(
        [
            'kubectl', 'exec', POD_NAME,
            '-n', POD_NAMESPACE,
            '-c', TARGET_CONTAINER,
            '--', 'sh', '-c', cmd,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise SFTPNoSuchFile(result.stderr or result.stdout or remote_path)
    lines = [line.strip() for line in (result.stdout or '').splitlines() if line.strip()]
    if len(lines) < 2:
        raise SFTPNoSuchFile(remote_path)
    kind = lines[-2]
    size_text, mtime_text = lines[-1].split()
    size = int(size_text)
    mtime = int(float(mtime_text))
    is_dir = kind == 'DIR'
    mode = stat.S_IFDIR | 0o755 if is_dir else stat.S_IFREG | 0o644
    # Build SFTPAttrs directly: from_local() requires st_*_ns on stat_result.
    return SFTPAttrs(
        type=FILEXFER_TYPE_DIRECTORY if is_dir else FILEXFER_TYPE_REGULAR,
        size=size,
        permissions=mode,
        uid=0,
        gid=0,
        atime=mtime,
        mtime=mtime,
    )


class KubectlSFTPServer(asyncssh.SFTPServer):
    """Expose workspace container files over SFTP/SCP via kubectl cp."""

    def __init__(self, chan: asyncssh.SSHServerChannel) -> None:
        self._staging = Path('/tmp/dohub-sftp') / secrets.token_hex(8)
        self._staging.mkdir(parents=True, exist_ok=True)
        super().__init__(chan)

    def _local_path(self, path: bytes) -> Path:
        remote = _normalize_container_path(path)
        rel = remote.lstrip('/')
        return self._staging / rel if rel else self._staging

    async def open(self, path: bytes, pflags: int, attrs: asyncssh.SFTPAttrs) -> _KubectlFile:
        remote_path = _normalize_container_path(path)
        local_path = self._local_path(path)
        writing = bool(pflags & FXF_WRITE)
        reading = bool(pflags & FXF_READ) or not writing
        create = bool(pflags & FXF_CREAT)
        truncate = bool(pflags & FXF_TRUNC)

        if writing:
            if pflags & FXF_EXCL and local_path.exists():
                raise SFTPFailure('File already exists')

            try:
                remote_attrs = await asyncio.to_thread(_kubectl_path_attrs, remote_path)
            except SFTPNoSuchFile:
                if not create:
                    raise
            else:
                if remote_attrs.type == FILEXFER_TYPE_DIRECTORY:
                    raise SFTPFailure('Is a directory')

            if not create and not truncate and not local_path.is_file():
                code, logs = await asyncio.to_thread(
                    _kubectl_cp_from_container, remote_path, local_path,
                )
                if code != 0 and not create:
                    LOG.warning('kubectl cp from container failed (%s): %s', remote_path, logs)
                    if not (pflags & FXF_CREAT):
                        raise SFTPNoSuchFile(logs or remote_path)

            if create or truncate or not local_path.is_file():
                local_path.parent.mkdir(parents=True, exist_ok=True)
                if truncate or create or not local_path.is_file():
                    local_path.write_bytes(b'')
            mode = 'rb+' if reading else 'wb'
            if pflags & FXF_APPEND:
                mode = 'ab+' if reading else 'ab'
            handle = _KubectlFile(local_path, remote_path, upload_on_close=True, mode=mode)
            LOG.info('SCP/SFTP upload open %s -> %s', remote_path, local_path)
            return handle

        code, logs = await asyncio.to_thread(_kubectl_cp_from_container, remote_path, local_path)
        if code != 0:
            LOG.warning('kubectl cp from container failed (%s): %s', remote_path, logs)
            raise SFTPNoSuchFile(logs or remote_path)

        mode = 'rb+'
        if pflags & FXF_APPEND:
            mode = 'ab+'
        handle = _KubectlFile(local_path, remote_path, upload_on_close=False, mode=mode)
        LOG.info('SCP/SFTP download open %s -> %s', remote_path, local_path)
        return handle

    async def close(self, file_obj: object) -> None:
        if not isinstance(file_obj, _KubectlFile):
            return super().close(file_obj)

        handle = file_obj
        handle.flush()
        handle.close()
        if handle.upload_on_close:
            code, logs, target = await asyncio.to_thread(
                _kubectl_cp_to_container, handle.local_path, handle.remote_path,
            )
            if code != 0:
                LOG.error('kubectl cp to container failed (%s): %s', target, logs)
                raise SFTPFailure(logs or 'upload failed')
            LOG.info('SCP/SFTP uploaded %s -> %s', handle.local_path, target)

    def read(self, file_obj: object, offset: int, size: int) -> bytes:
        handle = file_obj
        handle.seek(offset)
        return handle.read(size)

    def write(self, file_obj: object, offset: int, data: bytes) -> int:
        handle = file_obj
        handle.seek(offset)
        return handle.write(data)

    def fstat(self, file_obj: object) -> os.stat_result:
        if isinstance(file_obj, _KubectlFile):
            file_obj.flush()
            return os.stat(file_obj.local_path)
        return super().fstat(file_obj)

    def fsetstat(self, file_obj: object, attrs: asyncssh.SFTPAttrs) -> None:
        if isinstance(file_obj, _KubectlFile):
            file_obj.flush()
            if attrs.permissions is not None:
                with contextlib.suppress(OSError):
                    os.chmod(file_obj.local_path, attrs.permissions)
            atime = attrs.atime if attrs.atime is not None else attrs.mtime
            mtime = attrs.mtime if attrs.mtime is not None else attrs.atime
            if atime is not None and mtime is not None:
                with contextlib.suppress(OSError):
                    os.utime(file_obj.local_path, (atime, mtime))
            return None
        return super().fsetstat(file_obj, attrs)

    def setstat(self, path: bytes, attrs: asyncssh.SFTPAttrs) -> None:
        del path, attrs
        return None

    def lsetstat(self, path: bytes, attrs: asyncssh.SFTPAttrs) -> None:
        del path, attrs
        return None

    async def lstat(self, path: bytes) -> SFTPAttrs:
        remote_path = _normalize_container_path(path)
        return await asyncio.to_thread(_kubectl_path_attrs, remote_path)

    async def stat(self, path: bytes) -> SFTPAttrs:
        return await self.lstat(path)
