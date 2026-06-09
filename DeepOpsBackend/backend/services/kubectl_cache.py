"""In-memory TTL cache for kubectl / helm read commands."""

from __future__ import annotations

import copy
import json
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, TypeVar

T = TypeVar('T')

DEFAULT_TTL_SECONDS = 30

_lock = threading.Lock()
_cache: dict[str, tuple[float, Any]] = {}


def _cache_key(prefix: str, *parts: str) -> str:
    return prefix + ':' + ':'.join(str(part) for part in parts)


def get_cached(key: str, factory: Callable[[], T], ttl: float = DEFAULT_TTL_SECONDS) -> T:
    now = time.monotonic()
    with _lock:
        entry = _cache.get(key)
        if entry is not None and now - entry[0] < ttl:
            return copy.deepcopy(entry[1])

    value = factory()
    with _lock:
        _cache[key] = (now, copy.deepcopy(value))
    return copy.deepcopy(value)


def clear_kubectl_cache(prefix: str | None = None) -> None:
    with _lock:
        if prefix is None:
            _cache.clear()
            return
        for key in [k for k in _cache if k.startswith(prefix)]:
            del _cache[key]


@dataclass(frozen=True)
class CmdResult:
    returncode: int
    stdout: str
    stderr: str


def _run_subprocess(cmd: list[str], timeout: int) -> CmdResult:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
        return CmdResult(result.returncode, result.stdout or '', result.stderr or '')
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ''
        stderr = exc.stderr if isinstance(exc.stderr, str) else ''
        tail = '\n'.join(part for part in (stdout, stderr, 'command timed out') if part)
        return CmdResult(124, stdout, tail)


def kubectl_run(cmd: list[str], timeout: int = 60) -> CmdResult:
    key = _cache_key('kubectl_run', *cmd)
    return get_cached(key, lambda: _run_subprocess(cmd, timeout))


def kubectl_json(args: list[str], timeout: int = 60) -> dict | list | None:
    key = _cache_key('kubectl_json', *args)

    def factory() -> dict | list | None:
        result = _run_subprocess(['kubectl', *args, '-o', 'json'], timeout)
        if result.returncode != 0 or not result.stdout.strip():
            return None
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return None

    return get_cached(key, factory)


def helm_run(cmd: list[str], timeout: int = 60) -> CmdResult:
    key = _cache_key('helm_run', *cmd)
    return get_cached(key, lambda: _run_subprocess(cmd, timeout))
