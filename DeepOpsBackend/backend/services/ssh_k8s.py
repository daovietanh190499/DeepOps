"""Sync workspace SSH authorized_keys into the cluster."""

import os
import subprocess
import tempfile

from backend.services.k8s import NAMESPACE
from backend.services.k8s_status import live_workspace_state, workspace_is_active
from backend.services.ssh_keys import ssh_secret_name


def apply_ssh_secret(secret_name: str, public_key_openssh: str) -> tuple[str, int]:
    """Create or replace K8s secret with authorized_keys."""
    content = public_key_openssh.strip() + '\n'
    with tempfile.NamedTemporaryFile('w', suffix='.pub', delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    result = subprocess.run(
        [
            'kubectl', 'create', 'secret', 'generic', secret_name,
            f'--from-file=authorized_keys={tmp_path}',
            '-n', NAMESPACE,
            '--dry-run=client', '-o', 'yaml',
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return result.stderr or result.stdout, result.returncode

    try:
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
        os.unlink(tmp_path)


def restart_workspace_pod(release_name: str) -> tuple[str, int]:
    result = subprocess.run(
        [
            'kubectl', 'rollout', 'restart',
            f'deployment/{release_name}',
            '-n', NAMESPACE,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return (result.stdout or '') + (result.stderr or ''), result.returncode


def sync_workspace_ssh_to_cluster(workspace, *, public_key: str, respawn: bool = True) -> dict:
    """Apply secret and optionally re-helm / restart when the server is running."""
    from backend.services.k8s import build_spawn_config, create_codehub

    secret_name = ssh_secret_name(workspace)
    logs, code = apply_ssh_secret(secret_name, public_key)
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
    except ValueError as exc:
        out['ok'] = False
        out['error'] = str(exc)
        return out

    command, helm_logs, exit_code = create_codehub(config)
    out['helm_command'] = command
    out['helm_logs'] = helm_logs
    out['helm_code'] = exit_code
    out['restarted'] = exit_code == 0
    out['ok'] = exit_code == 0
    return out
