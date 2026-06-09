"""Cluster inspection via kubectl / microk8s (admin only)."""

import json
import re
import shutil
import subprocess
from datetime import datetime, timezone

from backend.services.kubectl_cache import DEFAULT_TTL_SECONDS, kubectl_json, kubectl_run


def _run(cmd: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    if cmd and cmd[0] == 'kubectl':
        result = kubectl_run(cmd, timeout=timeout)
        return subprocess.CompletedProcess(cmd, result.returncode, result.stdout, result.stderr)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )


def _run_json(cmd: list[str]) -> dict | list | None:
    if len(cmd) >= 2 and cmd[0] == 'kubectl':
        return kubectl_json(cmd[1:], timeout=60)
    result = _run(cmd)
    if result.returncode != 0 or not (result.stdout or '').strip():
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def get_microk8s_join_command() -> dict:
    """Run microk8s add-node on the host (when available)."""
    if not shutil.which('microk8s'):
        return {
            'ok': False,
            'error': 'microk8s CLI not found in this environment',
            'command': '',
            'raw': '',
        }
    result = _run(['microk8s', 'add-node'], timeout=120)
    raw = ((result.stdout or '') + (result.stderr or '')).strip()
    if result.returncode != 0:
        return {
            'ok': False,
            'error': 'microk8s add-node failed',
            'command': '',
            'raw': raw,
        }
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    join_lines = [ln for ln in lines if 'microk8s join' in ln or ln.startswith('microk8s join')]
    command = join_lines[-1] if join_lines else (lines[-1] if lines else raw)
    return {'ok': True, 'command': command, 'raw': raw, 'error': ''}


def _node_addresses(node: dict) -> dict:
    addrs = {'internal_ip': '', 'external_ip': '', 'hostname': ''}
    for addr in (node.get('status') or {}).get('addresses') or []:
        t = addr.get('type', '')
        v = addr.get('address', '')
        if t == 'InternalIP':
            addrs['internal_ip'] = v
        elif t == 'ExternalIP':
            addrs['external_ip'] = v
        elif t == 'Hostname':
            addrs['hostname'] = v
    return addrs


def _node_ready(node: dict) -> str:
    for cond in (node.get('status') or {}).get('conditions') or []:
        if cond.get('type') == 'Ready':
            return cond.get('status', 'Unknown')
    return 'Unknown'


def _node_roles(labels: dict) -> list[str]:
    roles = []
    for key in labels or {}:
        if key == 'node-role.kubernetes.io/control-plane' or key == 'node-role.kubernetes.io/master':
            roles.append('control-plane')
        elif key.startswith('node-role.kubernetes.io/'):
            roles.append(key.split('/', 1)[-1])
    return roles or ['worker']


def get_k8s_nodes() -> dict:
    data = _run_json(['kubectl', 'get', 'nodes', '-o', 'json'])
    if not data:
        err = _run(['kubectl', 'get', 'nodes'])
        return {
            'ok': False,
            'error': (err.stderr or err.stdout or 'failed to list nodes').strip(),
            'nodes': [],
        }
    nodes = []
    for item in data.get('items') or []:
        meta = item.get('metadata') or {}
        status = item.get('status') or {}
        info = status.get('nodeInfo') or {}
        cap = status.get('capacity') or {}
        alloc = status.get('allocatable') or {}
        addrs = _node_addresses(item)
        labels = meta.get('labels') or {}
        nodes.append({
            'name': meta.get('name', ''),
            'ready': _node_ready(item),
            'roles': _node_roles(labels),
            'internal_ip': addrs['internal_ip'],
            'external_ip': addrs['external_ip'],
            'hostname': addrs['hostname'],
            'kubelet_version': info.get('kubeletVersion', ''),
            'os_image': info.get('osImage', ''),
            'kernel': info.get('kernelVersion', ''),
            'container_runtime': info.get('containerRuntimeVersion', ''),
            'cpu_capacity': cap.get('cpu', ''),
            'memory_capacity': cap.get('memory', ''),
            'pods_allocatable': alloc.get('pods', ''),
            'created_at': meta.get('creationTimestamp', ''),
            'taints': len(status.get('taints') or []),
        })
    ready = sum(1 for n in nodes if n['ready'] == 'True')
    return {
        'ok': True,
        'nodes': nodes,
        'total': len(nodes),
        'ready': ready,
        'not_ready': len(nodes) - ready,
    }


def _directpv_header_key(label: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', label.strip().lower()).strip('_')


def _split_directpv_row(line: str) -> list[str]:
    if '│' not in line:
        return []
    cells = [c.strip() for c in line.split('│')]
    if cells and cells[0] == '':
        cells = cells[1:]
    if cells and cells[-1] == '':
        cells = cells[:-1]
    return cells


def _is_directpv_border_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if stripped[0] in '┌├└':
        return True
    # Separator rows use ┼ without leading │
    if '│' not in stripped and any(c in stripped for c in '┬┴┼─'):
        return True
    return False


def _parse_directpv_drives(raw: str) -> tuple[list[dict], list[dict]]:
    """Parse `kubectl directpv list drives` box-drawing table output."""
    header_keys: list[str] | None = None
    columns: list[dict] = []
    drives: list[dict] = []

    for line in raw.splitlines():
        if _is_directpv_border_line(line):
            continue
        cells = _split_directpv_row(line)
        if not cells:
            continue

        if header_keys is None:
            if any('drive' in c.lower() for c in cells):
                header_keys = [_directpv_header_key(c) for c in cells]
                columns = [{'key': k, 'label': lbl.strip()} for k, lbl in zip(header_keys, cells)]
            continue

        if len(cells) < len(header_keys):
            cells = cells + [''] * (len(header_keys) - len(cells))
        elif len(cells) > len(header_keys):
            cells = cells[: len(header_keys)]

        row = {header_keys[i]: cells[i] for i in range(len(header_keys))}
        if row.get('drive_id') or row.get('node') or row.get('name'):
            drives.append(row)

    return drives, columns


def get_directpv_drives() -> dict:
    if not shutil.which('kubectl'):
        return {'ok': False, 'error': 'kubectl not found', 'drives': [], 'columns': [], 'raw': ''}
    result = _run(['kubectl', 'directpv', 'list', 'drives'], timeout=90)
    stdout = (result.stdout or '').strip()
    raw = stdout
    if result.returncode != 0:
        raw = (stdout + '\n' + (result.stderr or '')).strip()
        return {
            'ok': False,
            'error': raw or 'kubectl directpv list drives failed',
            'drives': [],
            'columns': [],
            'raw': raw,
        }
    drives, columns = _parse_directpv_drives(stdout)
    parse_error = ''
    if 'DRIVE' in stdout.upper() and '│' in stdout and not drives:
        parse_error = 'could not parse directpv table output'
    return {
        'ok': not parse_error,
        'drives': drives,
        'columns': columns,
        'raw': stdout,
        'error': parse_error,
    }


def get_cluster_overview() -> dict:
    version_data = _run_json(['kubectl', 'version', '-o', 'json']) or {}
    cluster_info = _run(['kubectl', 'cluster-info'])
    ns_data = _run_json(['kubectl', 'get', 'namespaces', '-o', 'json']) or {}
    namespace_count = len((ns_data.get('items') or [])) if isinstance(ns_data, dict) else 0

    server = version_data.get('serverVersion') or {}
    client = version_data.get('clientVersion') or {}
    nodes_summary = get_k8s_nodes()

    return {
        'fetched_at': datetime.now(timezone.utc).isoformat(),
        'cache_ttl_seconds': DEFAULT_TTL_SECONDS,
        'cluster_info': (cluster_info.stdout or cluster_info.stderr or '').strip(),
        'client_version': client.get('gitVersion', ''),
        'server_version': server.get('gitVersion', ''),
        'platform': server.get('platform', ''),
        'namespace_count': namespace_count,
        'node_count': nodes_summary.get('total', 0),
        'nodes_ready': nodes_summary.get('ready', 0),
        'nodes_not_ready': nodes_summary.get('not_ready', 0),
    }
