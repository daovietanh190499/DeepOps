"""Map workspace GPU selector values to Kubernetes vGPU resource requests."""

from __future__ import annotations

from backend.services.platform_catalog import get_gpu_vram_map

# Legacy catalog values → vGPU count + gpumem (MiB).
_LEGACY_GPU_SPECS: dict[str, tuple[int, int]] = {
    'mig-2g.10gb': (1, 10 * 1024),
    'mig-3g.20gb': (1, 20 * 1024),
    'gpu': (1, 40 * 1024),
    'gpu:2': (2, 40 * 1024),
}

# Canonical vGPU catalog values for legacy template/option strings.
_LEGACY_GPU_ALIASES: dict[str, str] = {
    'mig-2g.10gb': '1:10240',
    'mig-3g.20gb': '1:20480',
    'gpu': '1:40960',
    'gpu:2': '2:20480',
}


def normalize_gpu_value(gpu: str | None) -> str:
    """Map legacy GPU selector strings to current vGPU catalog values."""
    raw = (gpu or '').strip()
    if not raw or raw in ('none', 'null'):
        return ''
    return _LEGACY_GPU_ALIASES.get(raw, raw)


def _vram_g_to_gpumem_mib(vram_g: int) -> int:
    return max(0, int(vram_g)) * 1024


def parse_gpu_resources(gpu: str | None) -> dict:
    """
    Parse a workspace/catalog GPU value into vGPU resources.

    Primary format:
      - none / empty: no GPU
      - "1": 1 vGPU, no gpumem limit
      - "1:1024": 1 vGPU + nvidia.com/gpumem=1024 (MiB)

    Legacy values (mig-*, gpu, gpu:2) are still accepted.
    """
    raw = normalize_gpu_value(gpu)
    if not raw:
        return {'enabled': False, 'count': 0, 'memory_mib': 0}

    if raw in _LEGACY_GPU_SPECS:
        count, memory_mib = _LEGACY_GPU_SPECS[raw]
        return {'enabled': True, 'count': count, 'memory_mib': memory_mib}

    if ':' in raw:
        count_part, mem_part = raw.split(':', 1)
        count = int(count_part)
        memory_mib = int(mem_part)
        if count <= 0:
            return {'enabled': False, 'count': 0, 'memory_mib': 0}
        return {'enabled': True, 'count': count, 'memory_mib': max(0, memory_mib)}

    if raw.isdigit():
        count = int(raw)
        if count <= 0:
            return {'enabled': False, 'count': 0, 'memory_mib': 0}
        vram_g = get_gpu_vram_map().get(raw, 0)
        memory_mib = _vram_g_to_gpumem_mib(vram_g) if vram_g else 0
        return {'enabled': True, 'count': count, 'memory_mib': memory_mib}

    # Unknown token — treat as legacy single-vGPU profile with catalog VRAM if present.
    vram_g = get_gpu_vram_map().get(raw, 0)
    memory_mib = _vram_g_to_gpumem_mib(vram_g) if vram_g else 0
    return {'enabled': True, 'count': 1, 'memory_mib': memory_mib}
