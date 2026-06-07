"""Sync workspace SSH authorized_keys into the cluster."""

import os
import subprocess
import tempfile

from backend.models import Workspace
from backend.services.k8s import build_spawn_config
from backend.services.k8s_env import NAMESPACE
from backend.services.k8s_status import live_workspace_state, workspace_is_active
from backend.services.ssh_keys import (
    ensure_host_key_material,
    get_or_none,
    ssh_secret_name,
)


def apply_ssh_bridge_secret(
    secret_name: str,
    public_key_openssh: str,
    host_key_openssh: str,
) -> tuple[str, int]:
    """Create or replace the ssh-bridge secret (authorized_keys + host_key)."""
    auth_content = public_key_openssh.strip() + '\n'
    host_content = host_key_openssh.strip() + '\n'
    auth_tmp = host_tmp = None
    try:
        with tempfile.NamedTemporaryFile('w', suffix='.pub', delete=False) as auth_file:
            auth_file.write(auth_content)
            auth_tmp = auth_file.name
        with tempfile.NamedTemporaryFile('w', suffix='.key', delete=False) as host_file:
            host_file.write(host_content)
            host_tmp = host_file.name

        result = subprocess.run(
            [
                'kubectl', 'create', 'secret', 'generic', secret_name,
                f'--from-file=authorized_keys={auth_tmp}',
                f'--from-file=host_key={host_tmp}',
                '-n', NAMESPACE,
                '--dry-run=client', '-o', 'yaml',
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return result.stderr or result.stdout, result.returncode

        apply = subprocess.run(
            ['kubectl', 'apply', '-f', '-'],
            input=result.stdout,
            capture_output=True,
            text=True,
            check=False,
        )
        logs = (apply.stdout or '') + (apply.stderr or '')
        return logs, apply.returncode
    finally:
        for path in (auth_tmp, host_tmp):
            if path:
                os.unlink(path)


def apply_ssh_secret(secret_name: str, public_key_openssh: str) -> tuple[str, int]:
    """Backward-compatible wrapper when only authorized_keys is provided."""
    return apply_ssh_bridge_secret(secret_name, public_key_openssh, '')


def sync_ssh_secret_for_workspace(workspace: Workspace) -> tuple[str, int]:
    """Push stored SSH keys from DB into the cluster secret."""
    record = get_or_none(workspace)
    if not record:
        return '', 0
    host_key = ensure_host_key_material(record)
    return apply_ssh_bridge_secret(
        ssh_secret_name(workspace),
        record.public_key,
        host_key,
    )


def restart_workspace_pod(release_name: str) -> tuple[str, int]:
    result = subprocess.run(
        [
            'kubectl', 'rollout', 'restart', 'deployment',
            '-n', NAMESPACE,
            f'-l=app.kubernetes.io/instance={release_name}',
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return (result.stdout or '') + (result.stderr or ''), result.returncode


def sync_workspace_ssh_to_cluster(workspace, *, public_key: str, respawn: bool = True) -> dict:
    """Apply secret and optionally re-helm when the server is running."""
    record = get_or_none(workspace)
    secret_name = ssh_secret_name(workspace)
    host_key = ensure_host_key_material(record) if record else ''
    logs, code = apply_ssh_bridge_secret(secret_name, public_key, host_key)
    out = {'secret': secret_name, 'apply_logs': logs, 'apply_code': code}
    if code != 0:
        out['ok'] = False
        return out

    if not respawn or not workspace_is_active(live_workspace_state(workspace)):
        out['ok'] = True
        out['restarted'] = False
        return out

    try:
        config = build_spawn_config(workspace)
        config['ssh_public_key'] = public_key
        if host_key:
            config['ssh_host_key'] = host_key
    except ValueError as exc:
        out['ok'] = False
        out['error'] = str(exc)
        return out

    from backend.services.k8s import create_codehub

    command, helm_logs, exit_code = create_codehub(config)
    out['helm_command'] = command
    out['helm_logs'] = helm_logs
    out['helm_code'] = exit_code
    out['restarted'] = exit_code == 0
    out['ok'] = exit_code == 0
    return out
