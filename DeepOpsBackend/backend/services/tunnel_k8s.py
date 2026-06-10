"""Sync workspace wstunnel port exposure into the cluster."""

from backend.models import Workspace
from backend.services.k8s import build_spawn_config, create_codehub
from backend.services.k8s_status import live_workspace_state, workspace_is_active


def sync_workspace_tunnel_to_cluster(workspace: Workspace, *, respawn: bool = True) -> dict:
    """Re-helm workspace release so port-tunnel sidecar matches ws_tunnel_ports."""
    out: dict = {'ok': True, 'restarted': False}

    if not respawn or not workspace_is_active(live_workspace_state(workspace)):
        out['message'] = 'Saved — start or restart the server to apply tunnel ports.'
        return out

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
        out['message'] = 'Tunnel ports applied — pod is updating.'
    else:
        out['error'] = (helm_logs or '').strip() or 'helm upgrade failed'
    return out
