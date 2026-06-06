"""Live resource status from the Kubernetes API (not persisted in DB)."""

import json
import subprocess

from backend.models import Workspace

from .drives_k8s import get_pvc_phase
from .k8s import NAMESPACE, get_codehub_workspace

# Re-export model states for mapping
STATE_OFFLINE = Workspace.STATE_OFFLINE
STATE_RUNNING = Workspace.STATE_RUNNING
STATE_PENDING_START = Workspace.STATE_PENDING_START
STATE_PENDING_STOP = Workspace.STATE_PENDING_STOP

DRIVE_BOUND = 'bound'
DRIVE_PENDING = 'pending'
DRIVE_LOST = 'lost'
DRIVE_NOT_FOUND = 'not_found'


def live_drive_status(claim_name: str) -> str:
    phase = get_pvc_phase(claim_name)
    if phase in ('', 'NotFound'):
        return DRIVE_NOT_FOUND
    if phase == 'Bound':
        return DRIVE_BOUND
    if phase in ('Pending', 'WaitForFirstConsumer'):
        return DRIVE_PENDING
    return DRIVE_LOST


def helm_release_exists(release_name: str) -> bool:
    result = subprocess.run(
        ['helm', 'list', '-n', NAMESPACE, '-f', f'^{release_name}$', '-q'],
        capture_output=True,
        text=True,
        check=False,
    )
    return bool((result.stdout or '').strip())


def deployment_replicas(release_name: str) -> int | None:
    """Desired replica count for the workspace deployment, or None if missing."""
    result = subprocess.run(
        [
            'kubectl', 'get', 'deployment',
            '-n', NAMESPACE,
            f'-l=app.kubernetes.io/instance={release_name}',
            '-o', 'jsonpath={.items[0].spec.replicas}',
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    out = (result.stdout or '').strip()
    if result.returncode != 0 or not out:
        return None
    try:
        return int(out)
    except ValueError:
        return None


def live_workspace_state(workspace: Workspace) -> str:
    """Derive workspace state from pod / helm release in the cluster."""
    try:
        pods = get_codehub_workspace(workspace)
        items = pods.get('items') or []
    except (json.JSONDecodeError, KeyError):
        items = []

    if items:
        phase = (items[0].get('status') or {}).get('phase', '')
        if phase == 'Running':
            return STATE_RUNNING
        if phase == 'Terminating':
            return STATE_PENDING_STOP
        if phase in ('Pending', 'ContainerCreating', 'PodInitializing'):
            return STATE_PENDING_START
        if phase in ('Failed', 'Unknown', 'CrashLoopBackOff', 'Error'):
            return STATE_PENDING_START

    if helm_release_exists(workspace.release_name):
        replicas = deployment_replicas(workspace.release_name)
        if replicas == 0:
            return STATE_OFFLINE
        return STATE_PENDING_START

    return STATE_OFFLINE


def workspace_is_active(state: str) -> bool:
    return state in (STATE_RUNNING, STATE_PENDING_START, STATE_PENDING_STOP)


def drive_is_in_use(drive) -> bool:
    for ws in Workspace.objects.filter(user_drive=drive).only('id', 'slug', 'user_id'):
        if workspace_is_active(live_workspace_state(ws)):
            return True
    return False
