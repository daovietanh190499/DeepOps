"""Sync workspace SSH authorized_keys into the cluster."""

import os
import subprocess
import tempfile

from backend.models import Workspace
from backend.services.k8s_env import NAMESPACE
from backend.services.k8s_status import live_workspace_state, workspace_is_active
from backend.services.sidecar_k8s import sync_workspace_sidecars
from backend.services.ssh_keys import (
    ensure_host_key_material,
    get_or_none,
    is_valid_openssh_private_key,
    is_valid_openssh_public_key,
    ssh_secret_name,
)


def apply_ssh_bridge_secret(
    secret_name: str,
    public_key_openssh: str,
    host_key_openssh: str,
) -> tuple[str, int]:
    """Create or replace the ssh-bridge secret (authorized_keys + host_key)."""
    if not secret_name:
        return 'missing ssh secret name', 1
    if not is_valid_openssh_public_key(public_key_openssh):
        return 'invalid authorized_keys public key', 1
    if not is_valid_openssh_private_key(host_key_openssh):
        return 'invalid ssh host private key', 1
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


def restart_workspace_deployment(workspace: Workspace) -> tuple[str, int]:
    """Restart the workspace pod so secret volume mounts are rebound."""
    release = (workspace.release_name or '').strip()
    if not release:
        return 'missing release name', 1
    result = subprocess.run(
        [
            'kubectl', 'rollout', 'restart', 'deployment',
            '-n', NAMESPACE,
            '-l', f'app.kubernetes.io/instance={release}',
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    logs = ((result.stdout or '') + (result.stderr or '')).strip()
    return logs, result.returncode


def sync_workspace_ssh_to_cluster(workspace, *, public_key: str, respawn: bool = True) -> dict:
    """Apply secret and update ssh-bridge sidecar via ConfigMap (no Helm redeploy)."""
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
        out['message'] = 'SSH keys saved — start the server to enable SSH.'
        return out

    sync = sync_workspace_sidecars(workspace, reload=False)
    out.update(sync)
    if not sync.get('ok'):
        out['ok'] = False
        out['restarted'] = False
        out['error'] = sync.get('error') or 'failed to update ssh sidecar config'
        return out

    restart_logs, restart_code = restart_workspace_deployment(workspace)
    out['restart_logs'] = restart_logs
    out['restart_code'] = restart_code
    out['restarted'] = restart_code == 0
    out['ok'] = restart_code == 0
    if restart_code == 0:
        out['message'] = 'SSH enabled — workspace restarted to load SSH keys.'
    else:
        out['error'] = restart_logs or 'failed to restart workspace for SSH'
    return out
