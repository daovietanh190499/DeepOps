"""Per-user resource limits from resource groups."""

from __future__ import annotations

import re

from backend.models import ResourceGroup, ResourceGroupMember, User

ALL_CPU = [2, 4, 8, 16, 32]
ALL_RAM = ['2G', '4G', '8G', '16G', '32G', '64G']
ALL_GPU = ['none', 'mig-2g.10gb', 'mig-3g.20gb', 'gpu', 'gpu:2']
ALL_DRIVE_SIZES = ['20Gi', '50Gi', '100Gi', '200Gi', '500Gi', '1Ti']

GPU_VRAM_GB = {
    '': 0,
    'none': 0,
    None: 0,
    'mig-2g.10gb': 10,
    'mig-3g.20gb': 20,
    'gpu': 40,
    'gpu:2': 80,
}


def parse_ram_g(ram: str) -> int:
    text = (ram or '').strip().upper()
    match = re.match(r'^(\d+)\s*G(?:I)?$', text)
    if match:
        return int(match.group(1))
    return 0


def parse_size_gi(size: str) -> int:
    text = (size or '').strip()
    if text.lower().endswith('ti'):
        return int(float(text[:-2]) * 1024)
    if text.lower().endswith('gi'):
        return int(float(text[:-2]))
    if text.lower().endswith('g'):
        return int(float(text[:-1]))
    return 0


def gpu_vram_g(gpu: str | None) -> int:
    key = (gpu or '').strip() or 'none'
    if key == 'none':
        return 0
    return GPU_VRAM_GB.get(key, 0)


def get_user_group(user: User) -> ResourceGroup | None:
    if user.role == User.ROLE_ADMIN:
        return None
    try:
        return user.resource_group_membership.group
    except ResourceGroupMember.DoesNotExist:
        return None


def limits_payload(group: ResourceGroup | None) -> dict | None:
    if group is None:
        return None
    return {
        'group_id': str(group.id),
        'group_name': group.name,
        'max_cpu': group.max_cpu,
        'max_ram_g': group.max_ram_g,
        'max_drive_size_gi': group.max_drive_size_gi,
        'max_gpu_vram_g': group.max_gpu_vram_g,
    }


def allowed_equipment(group: ResourceGroup | None) -> dict:
    if group is None:
        return {
            'cpu': ALL_CPU[:],
            'ram': ALL_RAM[:],
            'gpu': ALL_GPU[:],
            'drive_sizes': ALL_DRIVE_SIZES[:],
        }
    return {
        'cpu': [c for c in ALL_CPU if c <= group.max_cpu],
        'ram': [r for r in ALL_RAM if parse_ram_g(r) <= group.max_ram_g],
        'gpu': [g for g in ALL_GPU if gpu_vram_g(g) <= group.max_gpu_vram_g],
        'drive_sizes': [s for s in ALL_DRIVE_SIZES if parse_size_gi(s) <= group.max_drive_size_gi],
    }


def resource_limits_for_user(user: User) -> dict:
    group = get_user_group(user)
    limits = limits_payload(group)
    equipment = allowed_equipment(group)
    return {
        'limited': limits is not None,
        'limits': limits,
        'equipment': equipment,
    }


def validate_workspace_resources(user: User, *, cpu, ram, gpu) -> str | None:
    group = get_user_group(user)
    if group is None:
        return None
    try:
        cpu_val = int(cpu)
    except (TypeError, ValueError):
        return 'invalid cpu'
    if cpu_val > group.max_cpu:
        return f'CPU exceeds group limit ({group.max_cpu} vCPU)'
    ram_g = parse_ram_g(str(ram))
    if ram_g > group.max_ram_g:
        return f'RAM exceeds group limit ({group.max_ram_g}G)'
    vram = gpu_vram_g(gpu)
    if vram > group.max_gpu_vram_g:
        return f'GPU exceeds group VRAM limit ({group.max_gpu_vram_g}G)'
    return None


def validate_drive_size(user: User, size: str) -> str | None:
    group = get_user_group(user)
    if group is None:
        return None
    size_gi = parse_size_gi(size)
    if size_gi > group.max_drive_size_gi:
        return f'Drive size exceeds group limit ({group.max_drive_size_gi}Gi)'
    return None
