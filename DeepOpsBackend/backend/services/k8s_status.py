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


def get_deployment_status(release_name: str) -> dict | None:
    result = subprocess.run(
        [
            'kubectl', 'get', 'deployment',
            '-n', NAMESPACE,
            f'-l=app.kubernetes.io/instance={release_name}',
            '-o', 'json',
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not (result.stdout or '').strip():
        return None
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    items = data.get('items') or []
    if not items:
        return None
    dep = items[0]
    spec = dep.get('spec') or {}
    status = dep.get('status') or {}
    return {
        'name': dep.get('metadata', {}).get('name', ''),
        'desired': spec.get('replicas', 0) or 0,
        'ready': status.get('readyReplicas', 0) or 0,
        'available': status.get('availableReplicas', 0) or 0,
        'updated': status.get('updatedReplicas', 0) or 0,
        'unavailable': status.get('unavailableReplicas', 0) or 0,
    }


def deployment_replicas(release_name: str) -> int | None:
    dep = get_deployment_status(release_name)
    if dep is None:
        return None
    return dep['desired']


def _pod_ready_string(pod: dict) -> str:
    statuses = (pod.get('status') or {}).get('containerStatuses') or []
    if not statuses:
        return '0/0'
    ready = sum(1 for item in statuses if item.get('ready'))
    return f'{ready}/{len(statuses)}'


def _pod_k8s_display_status(pod: dict) -> str:
    """kubectl-style pod STATUS column."""
    meta = pod.get('metadata') or {}
    if meta.get('deletionTimestamp'):
        return 'Terminating'

    status = pod.get('status') or {}
    phase = status.get('phase', 'Unknown')

    for ics in status.get('initContainerStatuses') or []:
        state = ics.get('state') or {}
        if 'waiting' in state:
            reason = state['waiting'].get('reason', 'Init')
            return reason if reason.startswith('Init') else f'Init:{reason}'
        if 'terminated' in state:
            term = state['terminated']
            if term.get('exitCode', 0) != 0:
                return term.get('reason', 'Init:Error')

    for cs in status.get('containerStatuses') or []:
        state = cs.get('state') or {}
        if 'waiting' in state:
            return state['waiting'].get('reason', 'Pending')
        if 'terminated' in state:
            reason = state['terminated'].get('reason', 'Terminated')
            if reason != 'Completed':
                return reason

    container_statuses = status.get('containerStatuses') or []
    if phase == 'Running' and container_statuses:
        ready = sum(1 for item in container_statuses if item.get('ready'))
        if ready < len(container_statuses):
            return f'Running ({_pod_ready_string(pod)} ready)'
        return 'Running'

    return phase or 'Unknown'


def _workspace_k8s_display(deployment: dict | None, pod_rows: list[dict], release_exists: bool) -> str:
    if pod_rows:
        for pod in pod_rows:
            if pod.get('deleting') or pod.get('display') == 'Terminating':
                return 'Terminating'
        return pod_rows[0].get('display') or 'Unknown'

    if not release_exists:
        return 'Not deployed'

    if deployment:
        desired = deployment.get('desired', 0)
        if desired == 0:
            return 'Scaled down'
        ready = deployment.get('ready', 0)
        if ready < desired:
            return f'Pending ({ready}/{desired} ready)'
        return 'Running'

    return 'Unknown'


def live_workspace_k8s_status(workspace: Workspace) -> dict:
    """Live Kubernetes status for a workspace (pods + deployment)."""
    try:
        pods_data = get_codehub_workspace(workspace)
        items = pods_data.get('items') or []
    except (json.JSONDecodeError, KeyError):
        items = []

    deployment = get_deployment_status(workspace.release_name)
    release_exists = helm_release_exists(workspace.release_name)

    pod_rows = []
    for pod in items:
        meta = pod.get('metadata') or {}
        pod_rows.append({
            'name': meta.get('name', ''),
            'phase': (pod.get('status') or {}).get('phase', 'Unknown'),
            'display': _pod_k8s_display_status(pod),
            'ready': _pod_ready_string(pod),
            'deleting': bool(meta.get('deletionTimestamp')),
        })

    display = _workspace_k8s_display(deployment, pod_rows, release_exists)
    return {
        'display': display,
        'deployment': deployment,
        'pods': pod_rows,
        'release_exists': release_exists,
    }


def derive_workspace_state(k8s: dict) -> str:
    """Map live K8s status to action-oriented workspace state."""
    pods = k8s.get('pods') or []
    deployment = k8s.get('deployment')
    display = (k8s.get('display') or '').lower()

    if any(pod.get('deleting') for pod in pods):
        return STATE_PENDING_STOP
    if display == 'terminating':
        return STATE_PENDING_STOP

    for pod in pods:
        pod_display = (pod.get('display') or '').lower()
        if pod_display == 'running':
            return STATE_RUNNING
        if pod_display.startswith('running ('):
            return STATE_PENDING_START

    if not k8s.get('release_exists'):
        return STATE_OFFLINE

    if deployment and deployment.get('desired', 0) == 0:
        return STATE_OFFLINE

    if display in ('scaled down', 'not deployed'):
        return STATE_OFFLINE

    if display == 'running':
        return STATE_RUNNING

    if pods or (deployment and deployment.get('desired', 0) > 0):
        return STATE_PENDING_START

    return STATE_OFFLINE


def live_workspace_state(workspace: Workspace) -> str:
    return derive_workspace_state(live_workspace_k8s_status(workspace))


def workspace_is_active(state: str) -> bool:
    return state in (STATE_RUNNING, STATE_PENDING_START, STATE_PENDING_STOP)


def drive_is_in_use(drive) -> bool:
    for ws in Workspace.objects.filter(user_drive=drive).only('id', 'slug', 'user_id'):
        if workspace_is_active(live_workspace_state(ws)):
            return True
    return False
