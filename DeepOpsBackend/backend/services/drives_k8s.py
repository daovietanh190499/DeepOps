import json
import os
import subprocess
import tempfile

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
        return result.stdout + result.stderr, result.returncode
    finally:
        os.unlink(path)


def delete_drive_pvc(claim_name: str) -> int:
    return subprocess.call([
        'kubectl', 'delete', 'pvc', claim_name, '-n', NAMESPACE, '--ignore-not-found=true',
    ])


def get_pvc_phase(claim_name: str) -> str:
    result = subprocess.run(
        [
            'kubectl', 'get', 'pvc', claim_name,
            '-n', NAMESPACE,
            '-o', 'jsonpath={.status.phase}',
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return 'NotFound'
    return (result.stdout or '').strip() or 'NotFound'
