"""Apply workspace file-mount ConfigMaps to the cluster."""

from __future__ import annotations

import json
import subprocess

from backend.models import Workspace
from backend.services.k8s_env import NAMESPACE
from backend.services.workspace_file_mounts import file_mounts_payload


def file_mounts_configmap_name(workspace: Workspace) -> str:
    return f'{workspace.release_name}-file-mounts'


def build_file_mounts_config_data(workspace: Workspace) -> dict[str, str]:
    data: dict[str, str] = {}
    for row in file_mounts_payload(workspace, include_content=True):
        data[row['configmap_key']] = row['content']
    return data


def apply_workspace_file_configmap(workspace: Workspace) -> tuple[str, int]:
    data = build_file_mounts_config_data(workspace)
    name = file_mounts_configmap_name(workspace)

    if not data:
        return delete_workspace_file_configmap(workspace)

    manifest = {
        'apiVersion': 'v1',
        'kind': 'ConfigMap',
        'metadata': {
            'name': name,
            'namespace': NAMESPACE,
            'labels': {
                'app.kubernetes.io/instance': workspace.release_name,
            },
        },
        'data': data,
    }

    result = subprocess.run(
        ['kubectl', 'apply', '-f', '-'],
        input=json.dumps(manifest),
        capture_output=True,
        text=True,
        check=False,
    )
    logs = ((result.stdout or '') + (result.stderr or '')).strip()
    return logs, result.returncode


def delete_workspace_file_configmap(workspace: Workspace) -> tuple[str, int]:
    name = file_mounts_configmap_name(workspace)
    result = subprocess.run(
        ['kubectl', 'delete', 'configmap', name, '-n', NAMESPACE, '--ignore-not-found'],
        capture_output=True,
        text=True,
        check=False,
    )
    logs = ((result.stdout or '') + (result.stderr or '')).strip()
    return logs, result.returncode
