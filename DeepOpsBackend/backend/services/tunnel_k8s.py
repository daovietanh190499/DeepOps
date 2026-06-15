"""Sync workspace wstunnel port exposure into the cluster."""

from backend.models import Workspace
from backend.services.k8s_status import live_workspace_state, workspace_is_active
from backend.services.sidecar_k8s import sync_workspace_sidecars


def sync_workspace_tunnel_to_cluster(workspace: Workspace, *, respawn: bool = True) -> dict:
    """Update port-tunnel sidecar via ConfigMap (no Helm redeploy)."""
    out: dict = {'ok': True, 'restarted': False}

    if not respawn or not workspace_is_active(live_workspace_state(workspace)):
        out['message'] = 'Saved — start or restart the server to apply tunnel ports.'
        return out

    sync = sync_workspace_sidecars(workspace, reload=True)
    out.update(sync)
    if sync.get('ok'):
        ports = workspace.ws_tunnel_ports or []
        if ports:
            out['message'] = 'Tunnel ports applied — sidecar updated without restarting the workspace.'
        else:
            out['message'] = 'Tunnel disabled — sidecar idle.'
    else:
        out['error'] = sync.get('error') or 'failed to update port-tunnel sidecar'
    return out
