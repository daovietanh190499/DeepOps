"""Volume sizing helpers for DirectPV provisioning."""

import re

from .config import get_hub_config

_K8S_QUANTITY = re.compile(
    r'^([+-]?[0-9.]+)([eEinumkKMGTP]*[-+]?[0-9]*)$'
)

_BINARY_SUFFIXES = ('Ei', 'Pi', 'Ti', 'Gi', 'Mi', 'Ki')
_DECIMAL_SUFFIXES = ('E', 'P', 'T', 'G', 'M', 'K')


def drive_label_to_size(drive: str | None, default: str = '20Gi') -> str:
    """Map drive field to a valid Kubernetes storage quantity (e.g. 50Gi)."""
    if not drive:
        return default
    label = str(drive).strip()
    if not label:
        return default

    for suffix in _BINARY_SUFFIXES:
        if label.lower().endswith(suffix.lower()):
            num = label[: -len(suffix)]
            if num and _K8S_QUANTITY.match(num + suffix):
                return num + suffix

    for suffix in _DECIMAL_SUFFIXES:
        if label.lower().endswith(suffix.lower()) and not label.lower().endswith('i'):
            num = label[: -len(suffix)]
            if num:
                return num + suffix

    if label.lower().endswith('gb'):
        num = label[:-2].strip()
        if num:
            return f'{num}Gi'

    if _K8S_QUANTITY.match(label):
        return label

    return default
