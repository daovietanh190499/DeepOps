"""Sync workspace rclone backup config into the cluster."""

import os
import subprocess
import tempfile

from backend.models import Workspace
from backend.services.backup_config import backup_secret_name
from backend.services.k8s_env import NAMESPACE
from backend.services.k8s_status import live_workspace_state, workspace_is_active
from backend.services.sidecar_k8s import sync_workspace_sidecars


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


def sync_backup_secret_for_workspace(workspace: Workspace) -> tuple[str, int]:
    """Push rclone.conf from DB into the cluster secret."""
    config = (workspace.backup_rclone_config or '').strip()
    if not config:
        return '', 0
    return apply_backup_secret(backup_secret_name(workspace), config)


def sync_workspace_backup_to_cluster(workspace: Workspace, *, respawn: bool = True) -> dict:
    """Update backup secret + sidecar ConfigMap (no Helm redeploy)."""
    out: dict = {'ok': True, 'restarted': False}

    secret_logs, secret_code = sync_backup_secret_for_workspace(workspace)
    if secret_code != 0:
        return {
            'ok': False,
            'error': (secret_logs or '').strip() or 'failed to apply backup secret',
        }
    if secret_logs:
        out['secret_logs'] = secret_logs

    if not respawn:
        out['message'] = 'Backup settings saved.'
        return out

    if not workspace_is_active(live_workspace_state(workspace)):
        out['message'] = (
            'Backup settings saved — start the server to apply.'
            if workspace.backup_enabled
            else 'Backup settings saved.'
        )
        return out

    sync = sync_workspace_sidecars(workspace, reload=True)
    out.update(sync)
    if sync.get('ok'):
        out['message'] = (
            'Backup scheduled — cron started in sidecar.'
            if workspace.backup_enabled
            else 'Backup stopped — cron idle in sidecar.'
        )
    else:
        out['error'] = sync.get('error') or 'failed to update backup sidecar'
    return out
