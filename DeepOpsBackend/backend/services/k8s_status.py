"""Live resource status from the Kubernetes API (not persisted in DB)."""

import json
import subprocess

from backend.models import Workspace

from .drives_k8s import get_pvc_phase
from .k8s_env import NAMESPACE

# Re-export model states for mapping
STATE_OFFLINE = Workspace.STATE_OFFLINE
STATE_RUNNING = Workspace.STATE_RUNNING
STATE_PENDING_START = Workspace.STATE_PENDING_START
STATE_PENDING_STOP = Workspace.STATE_PENDING_STOP

DRIVE_BOUND = 'bound'
DRIVE_PENDING = 'pending'
DRIVE_LOST = 'lost'
DRIVE_NOT_FOUND = 'not_found'


def drive_status_from_pvc_phase(phase: str) -> str:
    if phase in ('', 'NotFound'):
        return DRIVE_NOT_FOUND
    if phase == 'Bound':
        return DRIVE_BOUND
    if phase in ('Pending', 'WaitForFirstConsumer'):
        return DRIVE_PENDING
    return DRIVE_LOST


def live_drive_status(claim_name: str, phase: str | None = None) -> str:
    if phase is None:
        phase = get_pvc_phase(claim_name)
    return drive_status_from_pvc_phase(phase)


def helm_release_names_set() -> set[str]:
    result = subprocess.run(
        ['helm', 'list', '-n', NAMESPACE, '-o', 'json'],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not (result.stdout or '').strip():
        return set()
    try:
        releases = json.loads(result.stdout)
    except json.JSONDecodeError:
        return set()
    return {
        (item.get('name') or '').strip()
        for item in releases
        if (item.get('name') or '').strip()
    }


def helm_release_exists(release_name: str) -> bool:
    return release_name in helm_release_names_set()


def _parse_deployment_item(dep: dict) -> dict:
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


def get_deployments_status_map(release_names: set[str]) -> dict[str, dict]:
    if not release_names:
        return {}

    from .drives_k8s import kubectl_json

    data = kubectl_json(['get', 'deployment', '-n', NAMESPACE])
    if not data:
        return {}

    result: dict[str, dict] = {}
    for dep in data.get('items') or []:
        labels = (dep.get('metadata') or {}).get('labels') or {}
        instance = labels.get('app.kubernetes.io/instance', '')
        if instance in release_names:
            result[instance] = _parse_deployment_item(dep)
    return result


def get_deployment_status(release_name: str) -> dict | None:
    return get_deployments_status_map({release_name}).get(release_name)


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


def _workspace_pods_by_id(workspace_ids: set[str]) -> dict[str, list[dict]]:
    if not workspace_ids:
        return {}

    from .drives_k8s import kubectl_json

    label_key = f'{NAMESPACE}-workspace-id'
    data = kubectl_json(['get', 'pod', '-n', NAMESPACE])
    pods_by_id: dict[str, list[dict]] = {ws_id: [] for ws_id in workspace_ids}
    if not data:
        return pods_by_id

    for pod in data.get('items') or []:
        meta = pod.get('metadata') or {}
        ws_id = (meta.get('labels') or {}).get(label_key, '')
        if ws_id not in workspace_ids:
            continue
        pods_by_id[ws_id].append({
            'name': meta.get('name', ''),
            'phase': (pod.get('status') or {}).get('phase', 'Unknown'),
            'display': _pod_k8s_display_status(pod),
            'ready': _pod_ready_string(pod),
            'deleting': bool(meta.get('deletionTimestamp')),
        })
    return pods_by_id


def _empty_workspace_k8s_status() -> dict:
    return {
        'display': 'Not deployed',
        'deployment': None,
        'pods': [],
        'release_exists': False,
    }


def _build_workspace_k8s_status(
    pod_rows: list[dict],
    deployment: dict | None,
    release_exists: bool,
) -> dict:
    display = _workspace_k8s_display(deployment, pod_rows, release_exists)
    return {
        'display': display,
        'deployment': deployment,
        'pods': pod_rows,
        'release_exists': release_exists,
    }


def live_workspace_k8s_status_batch(workspaces: list[Workspace]) -> dict[str, dict]:
    """Fetch live Kubernetes status for many workspaces with batched kubectl/helm calls."""
    ws_list = list(workspaces)
    if not ws_list:
        return {}

    ws_ids = {str(ws.id) for ws in ws_list}
    release_names = {ws.release_name for ws in ws_list}

    pods_by_id = _workspace_pods_by_id(ws_ids)
    deployments = get_deployments_status_map(release_names)
    helm_releases = helm_release_names_set()

    result: dict[str, dict] = {}
    for ws in ws_list:
        ws_id = str(ws.id)
        release = ws.release_name
        result[ws_id] = _build_workspace_k8s_status(
            pods_by_id.get(ws_id, []),
            deployments.get(release),
            release in helm_releases,
        )
    return result


def live_workspace_k8s_status(workspace: Workspace) -> dict:
    """Live Kubernetes status for a workspace (pods + deployment)."""
    return live_workspace_k8s_status_batch([workspace]).get(
        str(workspace.id),
        _empty_workspace_k8s_status(),
    )


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


def drives_in_use_map(drives, exclude_workspace_id=None) -> dict[str, bool]:
    """Return {drive_id: in_use} using batched workspace status lookups."""
    from backend.models import WorkspaceDriveMount

    drive_list = list(drives)
    if not drive_list:
        return {}

    drive_ids = [d.id for d in drive_list]
    result = {str(d.id): False for d in drive_list}
    drive_to_ws: dict[str, set[str]] = {str(d.id): set() for d in drive_list}
    related_ws: dict[str, Workspace] = {}

    for ws in Workspace.objects.filter(user_drive_id__in=drive_ids):
        if exclude_workspace_id and str(ws.id) == str(exclude_workspace_id):
            continue
        related_ws[str(ws.id)] = ws
        drive_to_ws[str(ws.user_drive_id)].add(str(ws.id))

    mount_qs = WorkspaceDriveMount.objects.filter(user_drive_id__in=drive_ids).select_related('workspace')
    if exclude_workspace_id:
        mount_qs = mount_qs.exclude(workspace_id=exclude_workspace_id)
    for mount in mount_qs:
        ws = mount.workspace
        related_ws[str(ws.id)] = ws
        drive_to_ws[str(mount.user_drive_id)].add(str(ws.id))

    if not related_ws:
        return result

    k8s_map = live_workspace_k8s_status_batch(list(related_ws.values()))
    states = {
        ws_id: derive_workspace_state(k8s_map.get(ws_id, _empty_workspace_k8s_status()))
        for ws_id in related_ws
    }

    for drive_id, ws_ids in drive_to_ws.items():
        for ws_id in ws_ids:
            if workspace_is_active(states.get(ws_id, STATE_OFFLINE)):
                result[drive_id] = True
                break
    return result


def workspace_is_active(state: str) -> bool:
    return state in (STATE_RUNNING, STATE_PENDING_START, STATE_PENDING_STOP)


def drive_is_in_use(drive, exclude_workspace_id=None) -> bool:
    return drives_in_use_map([drive], exclude_workspace_id=exclude_workspace_id).get(str(drive.id), False)
