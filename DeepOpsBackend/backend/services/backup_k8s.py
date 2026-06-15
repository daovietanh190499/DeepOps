"""Sync workspace rclone backup config into the cluster."""

import os
import subprocess
import tempfile

from backend.models import Workspace
from backend.services.backup_config import backup_secret_name
from backend.services.k8s import build_spawn_config, create_codehub
from backend.services.k8s_env import NAMESPACE
from backend.services.k8s_status import live_workspace_state, workspace_is_active


def apply_backup_secret(secret_name: str, rclone_config: str) -> tuple[str, int]:
    """Create or replace the backup sidecar secret (rclone.conf)."""
    content = rclone_config if rclone_config.endswith('\n') else rclone_config + '\n'
    conf_tmp = None
    try:
        with tempfile.NamedTemporaryFile('w', suffix='.conf', delete=False) as conf_file:
            conf_file.write(content)
            conf_tmp = conf_file.name

        result = subprocess.run(
            [
                'kubectl', 'create', 'secret', 'generic', secret_name,
                f'--from-file=rclone.conf={conf_tmp}',
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
        if conf_tmp:
            os.unlink(conf_tmp)


def sync_workspace_backup_to_cluster(workspace: Workspace, *, respawn: bool = True) -> dict:
    """Re-helm workspace release so backup sidecar matches DB config."""
    out: dict = {'ok': True, 'restarted': False}

    if not workspace.backup_enabled:
        out['message'] = 'Backup disabled — start or restart the server to remove the sidecar.'
        if not respawn or not workspace_is_active(live_workspace_state(workspace)):
            return out
    elif not respawn or not workspace_is_active(live_workspace_state(workspace)):
        out['message'] = 'Saved — start or restart the server to apply backup settings.'
        return out

    if workspace.backup_enabled:
        secret_logs, secret_code = apply_backup_secret(
            backup_secret_name(workspace),
            workspace.backup_rclone_config or '',
        )
        out['secret_logs'] = secret_logs
        if secret_code != 0:
            return {
                'ok': False,
                'error': (secret_logs or '').strip() or 'failed to apply backup secret',
            }

    try:
        config = build_spawn_config(workspace)
    except ValueError as exc:
        return {'ok': False, 'error': str(exc)}

    command, helm_logs, exit_code = create_codehub(config)
    out['helm_command'] = command
    out['helm_logs'] = helm_logs
    out['helm_code'] = exit_code
    out['restarted'] = exit_code == 0
    out['ok'] = exit_code == 0
    if exit_code == 0:
        if workspace.backup_enabled:
            out['message'] = 'Backup sidecar scheduled — pod is updating.'
        else:
            out['message'] = 'Backup sidecar removed — pod is updating.'
    else:
        out['error'] = (helm_logs or '').strip() or 'helm upgrade failed'
    return out
