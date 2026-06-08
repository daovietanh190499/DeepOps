"""DirectPV discover / init workflow (admin only)."""

import os
import shlex
import shutil
import subprocess
from pathlib import Path

import yaml

DRIVES_YAML_PATH = os.environ.get('DIRECTPV_DRIVES_YAML_PATH', '/tmp/directpv-drives.yaml')


def _run_cli(cmd: list[str], timeout: int = 280) -> subprocess.CompletedProcess:
    """
    Run a CLI command in a non-interactive environment.

    directpv discover uses a Bubble Tea TUI that requires /dev/tty; wrap with
    `script` when available so discover/init work from the Django container.
    """
    env = {**os.environ, 'TERM': 'dumb'}
    run_cmd = cmd
    if shutil.which('script'):
        shell_cmd = ' '.join(shlex.quote(part) for part in cmd)
        run_cmd = ['script', '-qefc', shell_cmd, '/dev/null']
    try:
        return subprocess.run(
            run_cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = (exc.stdout or '') if isinstance(exc.stdout, str) else ''
        stderr = (exc.stderr or '') if isinstance(exc.stderr, str) else ''
        tail = '\n'.join(part for part in (stdout, stderr, 'command timed out') if part)
        return subprocess.CompletedProcess(cmd, 124, stdout, tail)


def _drives_yaml_path() -> Path:
    return Path(DRIVES_YAML_PATH)


def _normalize_discover_data(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ValueError('invalid discover data')
    nodes = data.get('nodes') or []
    if not isinstance(nodes, list):
        raise ValueError('nodes must be a list')
    normalized_nodes = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        drives = []
        for drive in node.get('drives') or []:
            if not isinstance(drive, dict):
                continue
            sel = str(drive.get('select', 'no')).strip().lower()
            drives.append({
                **drive,
                'select': 'yes' if sel in ('yes', 'true', '1') else 'no',
            })
        normalized_nodes.append({
            'name': node.get('name', ''),
            'drives': drives,
        })
    return {
        'version': data.get('version') or 'v1',
        'nodes': normalized_nodes,
    }


def _write_drives_yaml(data: dict) -> None:
    path = _drives_yaml_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = _normalize_discover_data(data)
    with path.open('w', encoding='utf-8') as fh:
        yaml.safe_dump(
            normalized,
            fh,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )


def read_drives_yaml() -> dict:
    path = _drives_yaml_path()
    if not path.is_file():
        return {
            'ok': True,
            'exists': False,
            'path': str(path),
            'data': None,
            'error': '',
        }
    try:
        with path.open(encoding='utf-8') as fh:
            data = yaml.safe_load(fh)
    except (OSError, yaml.YAMLError) as exc:
        return {
            'ok': False,
            'exists': True,
            'path': str(path),
            'data': None,
            'error': f'failed to read drives.yaml: {exc}',
        }
    if not data:
        return {
            'ok': True,
            'exists': False,
            'path': str(path),
            'data': None,
            'error': '',
        }
    return {
        'ok': True,
        'exists': True,
        'path': str(path),
        'data': _normalize_discover_data(data),
        'error': '',
    }


def discover_drives() -> dict:
    if not shutil.which('kubectl'):
        return {'ok': False, 'error': 'kubectl not found', 'data': None, 'raw': '', 'path': DRIVES_YAML_PATH}

    path = _drives_yaml_path()
    if path.exists():
        path.unlink()

    result = _run_cli(
        ['kubectl', 'directpv', 'discover', '--output-file', str(path)],
        timeout=280,
    )
    stdout = (result.stdout or '').strip()
    stderr = (result.stderr or '').strip()
    raw = '\n'.join(part for part in (stdout, stderr) if part).strip()

    if result.returncode != 0:
        return {
            'ok': False,
            'error': raw or 'kubectl directpv discover failed',
            'data': None,
            'raw': raw,
            'path': str(path),
        }

    if not path.is_file():
        return {
            'ok': True,
            'message': 'No drives discovered',
            'data': None,
            'raw': raw,
            'path': str(path),
        }

    loaded = read_drives_yaml()
    return {
        'ok': loaded['ok'],
        'message': 'Drives discovered',
        'data': loaded.get('data'),
        'error': loaded.get('error', ''),
        'raw': raw,
        'path': str(path),
    }


def save_drives_yaml(data: dict) -> dict:
    path = _drives_yaml_path()
    try:
        normalized = _normalize_discover_data(data)
        _write_drives_yaml(normalized)
    except ValueError as exc:
        return {'ok': False, 'error': str(exc), 'path': str(path)}
    except OSError as exc:
        return {'ok': False, 'error': f'failed to write drives.yaml: {exc}', 'path': str(path)}
    return {
        'ok': True,
        'path': str(path),
        'data': normalized,
    }


def init_drives() -> dict:
    if not shutil.which('kubectl'):
        return {'ok': False, 'error': 'kubectl not found', 'raw': '', 'path': DRIVES_YAML_PATH}

    path = _drives_yaml_path()
    if not path.is_file():
        return {
            'ok': False,
            'error': 'drives.yaml not found — run discover first',
            'raw': '',
            'path': str(path),
        }

    loaded = read_drives_yaml()
    if not loaded.get('data'):
        return {
            'ok': False,
            'error': 'drives.yaml is empty — run discover first',
            'raw': '',
            'path': str(path),
        }

    selected = sum(
        1
        for node in loaded['data'].get('nodes') or []
        for drive in node.get('drives') or []
        if drive.get('select') == 'yes'
    )
    if selected == 0:
        return {
            'ok': False,
            'error': 'No drives selected for init (set select to "yes" on at least one drive)',
            'raw': '',
            'path': str(path),
        }

    result = _run_cli(
        ['kubectl', 'directpv', 'init', str(path), '--dangerous'],
        timeout=280,
    )
    stdout = (result.stdout or '').strip()
    stderr = (result.stderr or '').strip()
    raw = '\n'.join(part for part in (stdout, stderr) if part).strip()

    if result.returncode != 0:
        return {
            'ok': False,
            'error': raw or 'kubectl directpv init failed',
            'raw': raw,
            'path': str(path),
        }

    return {
        'ok': True,
        'message': f'Initialized {selected} drive(s)',
        'raw': raw,
        'path': str(path),
    }
