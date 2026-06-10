"""kubectl logs/describe for workspace pods."""

import subprocess

from backend.models import Workspace

from .k8s_env import NAMESPACE
from .k8s_status import workspace_pods_for_id


def _kubectl(args: list[str], timeout: int = 60) -> tuple[str, str, int]:
    result = subprocess.run(
        ['kubectl', *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )
    return result.stdout or '', result.stderr or '', result.returncode


def _pod_container_names(pod_name: str) -> list[str]:
    stdout, _, code = _kubectl([
        'get', 'pod', pod_name,
        '-n', NAMESPACE,
        '-o', 'jsonpath={.spec.containers[*].name}',
    ])
    if code != 0:
        return []
    return [name for name in stdout.split() if name]


def workspace_logs(
    workspace: Workspace,
    *,
    pod_name: str | None = None,
    container: str | None = None,
    tail: int = 500,
) -> dict:
    pods = workspace_pods_for_id(str(workspace.id))
    if not pods:
        return {
            'logs': '',
            'pods': [],
            'selected_pod': '',
            'containers': [],
            'selected_container': container or '',
            'error': 'No pods found. The server may be stopped or not deployed yet.',
        }

    selected = pod_name or pods[0]['name']
    if not any(item['name'] == selected for item in pods):
        selected = pods[0]['name']

    tail_n = max(50, min(int(tail or 500), 5000))
    args = [
        'logs', selected,
        '-n', NAMESPACE,
        f'--tail={tail_n}',
        '--timestamps',
    ]
    if container:
        args.extend(['-c', container])
    else:
        args.extend(['--all-containers=true', '--prefix=true'])

    stdout, stderr, code = _kubectl(args)
    logs = stdout.strip()
    if not logs and stderr:
        logs = stderr.strip()
    if not logs:
        logs = '(no log output)'

    containers = _pod_container_names(selected)
    error = ''
    if code != 0:
        error = stderr.strip() or 'kubectl logs failed'

    return {
        'logs': logs,
        'pods': pods,
        'selected_pod': selected,
        'containers': containers,
        'selected_container': container or '',
        'error': error,
    }


def workspace_describe(
    workspace: Workspace,
    *,
    pod_name: str | None = None,
) -> dict:
    release = workspace.release_name
    pods = workspace_pods_for_id(str(workspace.id))
    sections: list[str] = []

    dep_out, dep_err, dep_code = _kubectl([
        'describe', 'deployment',
        '-n', NAMESPACE,
        '-l', f'app.kubernetes.io/instance={release}',
    ])
    if dep_out.strip():
        sections.append(dep_out.strip())
    elif dep_code != 0 and dep_err.strip():
        sections.append(f'# Deployment\n{dep_err.strip()}')

    target_pods = pods
    if pod_name:
        matched = [item for item in pods if item['name'] == pod_name]
        if matched:
            target_pods = matched

    if not target_pods:
        sections.append('# Pods\nNo pods found for this workspace.')
    else:
        for pod in target_pods:
            pod_out, pod_err, pod_code = _kubectl([
                'describe', 'pod', pod['name'],
                '-n', NAMESPACE,
            ])
            if pod_out.strip():
                sections.append(pod_out.strip())
            elif pod_err.strip():
                sections.append(f'# Pod {pod["name"]}\n{pod_err.strip()}')
            elif pod_code != 0:
                sections.append(f'# Pod {pod["name"]}\n(describe failed)')

    text = '\n\n'.join(sections) if sections else 'Nothing to describe (server not deployed).'
    return {
        'text': text,
        'pods': pods,
        'selected_pod': pod_name or (pods[0]['name'] if pods else ''),
        'release_name': release,
    }
