"""Runtime sidecar control via ConfigMap (no Helm redeploy for config changes)."""

from __future__ import annotations

import json
import shlex
import subprocess

from backend.models import Workspace
from backend.services.backup_config import parse_backup_mount_selection
from backend.services.k8s_env import NAMESPACE
from backend.services.k8s_status import live_workspace_state, workspace_is_active
from backend.services.ssh_keys import (
    ensure_host_key_material,
    get_or_none,
    is_valid_openssh_private_key,
    is_valid_openssh_public_key,
    ssh_keys_ready,
)
from backend.services.tunnel_ports import parse_tunnel_ports


def sidecar_configmap_name(workspace: Workspace) -> str:
    return f'{workspace.release_name}-codehub-sidecar-config'


def build_sidecar_config_data(workspace: Workspace) -> dict[str, str]:
    backup_folders: list[str] = []
    if workspace.backup_enabled:
        try:
            backup_folders = parse_backup_mount_selection(workspace, workspace.backup_folders)
        except ValueError:
            backup_folders = []

    ssh_record = get_or_none(workspace)
    ssh_enabled = ssh_keys_ready(ssh_record)
    tunnel_ports = workspace.ws_tunnel_ports or []
    if not isinstance(tunnel_ports, list):
        tunnel_ports = []
    try:
        tunnel_ports = parse_tunnel_ports(tunnel_ports)
    except ValueError:
        tunnel_ports = []

    return {
        'backup.json': json.dumps({
            'enabled': bool(workspace.backup_enabled),
            'schedule': workspace.backup_schedule or '',
            'remote': workspace.backup_remote or '',
            'folders': backup_folders,
        }),
        'ssh.json': json.dumps({
            'enabled': ssh_enabled,
            'exec_shell': workspace.exec_shell or Workspace.EXEC_SHELL_BASH,
        }),
        'tunnel.json': json.dumps({
            'enabled': bool(tunnel_ports),
            'ports': tunnel_ports,
        }),
        'monitor.json': json.dumps({
            'enabled': True,
        }),
    }


def apply_sidecar_configmap(workspace: Workspace) -> tuple[str, int]:
    data = build_sidecar_config_data(workspace)
    name = sidecar_configmap_name(workspace)

    manifest = {
        'apiVersion': 'v1',
        'kind': 'ConfigMap',
        'metadata': {
            'name': name,
            'namespace': NAMESPACE,
            'labels': {
                'app.kubernetes.io/instance': workspace.release_name,
            },
        },
        'data': data,
    }

    result = subprocess.run(
        ['kubectl', 'apply', '-f', '-'],
        input=json.dumps(manifest),
        capture_output=True,
        text=True,
        check=False,
    )
    logs = ((result.stdout or '') + (result.stderr or '')).strip()
    return logs, result.returncode


def _resolve_workspace_pod(workspace: Workspace) -> str:
    from backend.services.workspace_kubectl import workspace_pods_for_id

    pods = workspace_pods_for_id(str(workspace.id))
    if not pods:
        return ''
    return pods[0]['name']


def push_port_tunnel_runtime_config(workspace: Workspace, pod: str) -> tuple[str, int]:
    """Apply tunnel ports immediately via writable override (ConfigMap mounts can lag)."""
    try:
        ports = parse_tunnel_ports(workspace.ws_tunnel_ports)
    except ValueError as exc:
        return str(exc), 1

    payload = json.dumps({'enabled': bool(ports), 'ports': ports})
    shell_cmd = '; '.join([
        'mkdir -p /tmp/sidecar',
        f'printf %s {shlex.quote(payload)} > /tmp/sidecar/tunnel.json',
        'kill -HUP 1',
    ])
    result = subprocess.run(
        [
            'kubectl', 'exec', pod,
            '-n', NAMESPACE,
            '-c', 'port-tunnel',
            '--', 'sh', '-c', shell_cmd,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    logs = ((result.stdout or '') + (result.stderr or '')).strip()
    return logs, result.returncode


def push_ssh_bridge_runtime_keys(
    workspace: Workspace,
    pod: str,
    *,
    public_key: str,
    host_key: str,
) -> tuple[str, int]:
    """Push SSH keys into ssh-bridge immediately (secret volume mounts can lag)."""
    if not is_valid_openssh_public_key(public_key):
        return 'invalid authorized_keys public key', 1
    if not is_valid_openssh_private_key(host_key):
        return 'invalid ssh host private key', 1

    auth_content = public_key.strip() + '\n'
    host_content = host_key.strip() + '\n'
    shell_cmd = '; '.join([
        'mkdir -p /tmp/sidecar/ssh',
        f'printf %s {shlex.quote(auth_content)} > /tmp/sidecar/ssh/authorized_keys',
        f'printf %s {shlex.quote(host_content)} > /tmp/sidecar/ssh/host_key',
        'chmod 600 /tmp/sidecar/ssh/authorized_keys /tmp/sidecar/ssh/host_key',
        'kill -HUP 1',
    ])
    result = subprocess.run(
        [
            'kubectl', 'exec', pod,
            '-n', NAMESPACE,
            '-c', 'ssh-bridge',
            '--', 'sh', '-c', shell_cmd,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    logs = ((result.stdout or '') + (result.stderr or '')).strip()
    return logs, result.returncode


def reload_sidecar_supervisors(workspace: Workspace) -> dict:
    """Signal sidecar supervisors to reload ConfigMap state immediately."""
    pod = _resolve_workspace_pod(workspace)
    if not pod:
        return {'ok': False, 'error': 'no running pod found'}

    logs: list[str] = []
    failures = 0

    ssh_record = get_or_none(workspace)
    if ssh_record and ssh_keys_ready(ssh_record):
        host_key = ensure_host_key_material(ssh_record)
        ssh_logs, ssh_code = push_ssh_bridge_runtime_keys(
            workspace,
            pod,
            public_key=ssh_record.public_key,
            host_key=host_key,
        )
        if ssh_logs:
            logs.append(f'ssh-bridge: {ssh_logs}')
        if ssh_code != 0:
            failures += 1

    containers = ('backup-sidecar', 'ssh-bridge', 'monitor-sidecar')
    for container in containers:
        # Minimal images lack /bin/kill; use shell builtin instead.
        result = subprocess.run(
            [
                'kubectl', 'exec', pod,
                '-n', NAMESPACE,
                '-c', container,
                '--', 'sh', '-c', 'kill -HUP 1',
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        chunk = ((result.stdout or '') + (result.stderr or '')).strip()
        if chunk:
            logs.append(f'{container}: {chunk}')
        if result.returncode != 0:
            failures += 1

    tunnel_logs, tunnel_code = push_port_tunnel_runtime_config(workspace, pod)
    if tunnel_logs:
        logs.append(f'port-tunnel: {tunnel_logs}')
    if tunnel_code != 0:
        failures += 1

    return {
        'ok': failures == 0,
        'logs': '\n'.join(logs),
        'pod': pod,
    }


def sync_workspace_sidecars(workspace: Workspace, *, reload: bool = True) -> dict:
    """Apply sidecar ConfigMap from DB and optionally reload running supervisors."""
    ssh_record = get_or_none(workspace)
    if ssh_keys_ready(ssh_record):
        from backend.services.ssh_k8s import sync_ssh_secret_for_workspace

        ssh_logs, ssh_code = sync_ssh_secret_for_workspace(workspace)
        if ssh_code != 0:
            return {
                'ok': False,
                'error': ssh_logs or 'failed to apply ssh secret',
                'apply_code': ssh_code,
                'restarted': False,
            }

    from backend.services.backup_k8s import sync_backup_secret_for_workspace

    backup_logs, backup_code = sync_backup_secret_for_workspace(workspace)
    if backup_code != 0:
        return {
            'ok': False,
            'error': backup_logs or 'failed to apply backup secret',
            'apply_code': backup_code,
            'restarted': False,
        }

    logs, code = apply_sidecar_configmap(workspace)
    out: dict = {
        'ok': code == 0,
        'configmap': sidecar_configmap_name(workspace),
        'apply_logs': logs,
        'apply_code': code,
        'restarted': False,
    }
    if code != 0:
        out['error'] = logs or 'failed to apply sidecar configmap'
        return out

    if reload and workspace_is_active(live_workspace_state(workspace)):
        reload_out = reload_sidecar_supervisors(workspace)
        out['reload'] = reload_out
        out['restarted'] = reload_out.get('ok', False)
        if not reload_out.get('ok'):
            out['reload_warning'] = (
                reload_out.get('logs')
                or 'immediate reload signal failed; sidecars will apply config within a few seconds'
            )

    return out
