import json
import os
import subprocess
import tempfile

from backend.services.kubectl_cache import clear_kubectl_cache, kubectl_json, kubectl_run

from .config import get_hub_config
from .storage import drive_label_to_size

from .k8s_env import NAMESPACE


def _storage_class() -> str:
    return get_hub_config().get('storage', {}).get('storageClassName', 'directpv-min-io')


def _volume_mode() -> str:
    return get_hub_config().get('storage', {}).get('volumeMode', 'Filesystem')


def normalize_size(size: str) -> str:
    return drive_label_to_size(size, '20Gi')


def create_drive_pvc(claim_name: str, size: str, username: str, drive_id: str) -> tuple[str, int]:
    """Create a standalone DirectPV PVC for a user drive."""
    quantity = normalize_size(size)
    manifest = {
        'apiVersion': 'v1',
        'kind': 'PersistentVolumeClaim',
        'metadata': {
            'name': claim_name,
            'namespace': NAMESPACE,
            'labels': {
                f'{NAMESPACE}-username': username,
                f'{NAMESPACE}-drive-id': drive_id,
                'app.kubernetes.io/managed-by': 'dohub',
            },
        },
        'spec': {
            'storageClassName': _storage_class(),
            'volumeMode': _volume_mode(),
            'accessModes': ['ReadWriteOnce'],
            'resources': {'requests': {'storage': quantity}},
        },
    }
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
        json.dump(manifest, tmp)
        path = tmp.name
    try:
        result = subprocess.run(
            ['kubectl', 'apply', '-f', path],
            capture_output=True,
            text=True,
            check=False,
        )
        clear_kubectl_cache()
        return result.stdout + result.stderr, result.returncode
    finally:
        os.unlink(path)


def delete_drive_pvc(claim_name: str) -> int:
    code = subprocess.call([
        'kubectl', 'delete', 'pvc', claim_name, '-n', NAMESPACE, '--ignore-not-found=true',
    ])
    if code == 0:
        clear_kubectl_cache()
    return code


def get_pvc_phase(claim_name: str) -> str:
    result = kubectl_run([
        'kubectl', 'get', 'pvc', claim_name,
        '-n', NAMESPACE,
        '-o', 'jsonpath={.status.phase}',
    ])
    if result.returncode != 0:
        return 'NotFound'
    return (result.stdout or '').strip() or 'NotFound'


def _kubectl_json(args: list[str]) -> dict | None:
    data = kubectl_json(args)
    return data if isinstance(data, dict) else None


def _node_from_pv(pv: dict) -> str:
    labels = (pv.get('metadata') or {}).get('labels') or {}
    node = labels.get('directpv.min.io/node', '')
    if node:
        return node

    csi = (pv.get('spec') or {}).get('csi') or {}
    attrs = csi.get('volumeAttributes') or {}
    for key in ('node', 'nodeID', 'directpv.min.io/node'):
        value = attrs.get(key)
        if value:
            return str(value)

    affinity = (pv.get('spec') or {}).get('nodeAffinity') or {}
    required = affinity.get('required') or {}
    for term in required.get('nodeSelectorTerms') or []:
        for expr in term.get('matchExpressions') or []:
            if expr.get('key') == 'kubernetes.io/hostname' and expr.get('values'):
                return str(expr['values'][0])
    return ''


def _node_from_directpv_volume(item: dict) -> str:
    labels = (item.get('metadata') or {}).get('labels') or {}
    node = labels.get('directpv.min.io/node', '')
    if node:
        return node
    status = item.get('status') or {}
    for topo in status.get('preferredAccessibleTopology') or []:
        hostname = topo.get('kubernetes.io/hostname')
        if hostname:
            return str(hostname)
    return ''


def _build_pv_node_map(pv_names: set[str]) -> dict[str, str]:
    if not pv_names:
        return {}

    pv_nodes: dict[str, str] = {}
    pv_data = _kubectl_json(['get', 'pv'])
    if pv_data:
        for item in pv_data.get('items') or []:
            name = (item.get('metadata') or {}).get('name', '')
            if name in pv_names:
                pv_nodes[name] = _node_from_pv(item)

    missing = {name for name in pv_names if not pv_nodes.get(name)}
    if not missing:
        return pv_nodes

    for crd in (
        'directpvvolumes.directpv.min.io',
        'directpvvolumes',
    ):
        dpv_data = _kubectl_json(['get', crd, '-A'])
        if not dpv_data:
            continue
        for item in dpv_data.get('items') or []:
            name = (item.get('metadata') or {}).get('name', '')
            if name not in missing:
                continue
            node = _node_from_directpv_volume(item)
            if node:
                pv_nodes[name] = node
        if all(pv_nodes.get(name) for name in missing):
            break

    return pv_nodes


def get_pvc_placement_map(claim_names: list[str]) -> dict[str, dict]:
    """Resolve bound PVC claim names to PV and Kubernetes node."""
    wanted = {name for name in claim_names if name}
    empty = {'node': '', 'pv_name': ''}
    if not wanted:
        return {}

    pvc_data = _kubectl_json(['get', 'pvc', '-n', NAMESPACE])
    if not pvc_data:
        return {name: dict(empty) for name in wanted}

    claim_to_pv: dict[str, str] = {}
    for item in pvc_data.get('items') or []:
        meta = item.get('metadata') or {}
        claim = meta.get('name', '')
        if claim not in wanted:
            continue
        status = item.get('status') or {}
        if status.get('phase') != 'Bound':
            continue
        spec = item.get('spec') or {}
        pv_name = spec.get('volumeName') or ''
        if pv_name:
            claim_to_pv[claim] = pv_name

    pv_nodes = _build_pv_node_map(set(claim_to_pv.values()))
    return {
        claim: {
            'node': pv_nodes.get(claim_to_pv.get(claim, ''), ''),
            'pv_name': claim_to_pv.get(claim, ''),
        }
        for claim in wanted
    }


def get_pvc_placement(claim_name: str) -> dict:
    return get_pvc_placement_map([claim_name]).get(
        claim_name,
        {'node': '', 'pv_name': ''},
    )
