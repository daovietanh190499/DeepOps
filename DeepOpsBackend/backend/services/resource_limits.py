"""Per-user resource limits from resource groups."""

from __future__ import annotations

import re

from backend.models import ResourceGroup, ResourceGroupMember, User, UserDrive, Workspace
from backend.services.gpu_resources import normalize_gpu_value
from backend.services.platform_catalog import (
    all_cpu,
    all_drive_sizes,
    all_gpu,
    all_ram,
    get_gpu_vram_map,
    parse_cpu_value,
)


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
    key = normalize_gpu_value(gpu) or 'none'
    if key == 'none':
        return 0
    mapped = get_gpu_vram_map().get(key)
    if mapped is not None:
        return mapped
    if ':' in key:
        try:
            mem_mib = int(key.split(':', 1)[1])
            return max(1, mem_mib // 1024) if mem_mib > 0 else 0
        except ValueError:
            return 0
    return 0


def get_user_group(user: User) -> ResourceGroup | None:
    if user.role == User.ROLE_ADMIN:
        return None
    try:
        return user.resource_group_membership.group
    except ResourceGroupMember.DoesNotExist:
        return None


def user_drive_count(user: User) -> int:
    return UserDrive.objects.filter(user=user).count()


def user_server_count(user: User) -> int:
    return Workspace.objects.filter(user=user).count()


def limits_payload(group: ResourceGroup | None, user: User | None = None) -> dict | None:
    if group is None:
        return None
    payload = {
        'group_id': str(group.id),
        'group_name': group.name,
        'max_cpu': group.max_cpu,
        'max_ram_g': group.max_ram_g,
        'max_drive_size_gi': group.max_drive_size_gi,
        'max_gpu_vram_g': group.max_gpu_vram_g,
        'max_servers': group.max_servers,
        'max_drives': group.max_drives,
        'can_change_privileged': group.can_change_privileged,
    }
    if user is not None:
        payload['server_count'] = user_server_count(user)
        payload['drive_count'] = user_drive_count(user)
    return payload


def allowed_equipment(group: ResourceGroup | None) -> dict:
    cpus = all_cpu()
    rams = all_ram()
    gpus = all_gpu()
    drive_sizes = all_drive_sizes()
    if group is None:
        return {
            'cpu': cpus[:],
            'ram': rams[:],
            'gpu': gpus[:],
            'drive_sizes': drive_sizes[:],
        }
    return {
        'cpu': [c for c in cpus if c <= group.max_cpu],
        'ram': [r for r in rams if parse_ram_g(r) <= group.max_ram_g],
        'gpu': [g for g in gpus if gpu_vram_g(g) <= group.max_gpu_vram_g],
        'drive_sizes': [s for s in drive_sizes if parse_size_gi(s) <= group.max_drive_size_gi],
    }


def can_change_privileged(user: User) -> bool:
    if user.role == User.ROLE_ADMIN:
        return True
    group = get_user_group(user)
    if group is None:
        return False
    return group.can_change_privileged


def resource_limits_for_user(user: User) -> dict:
    group = get_user_group(user)
    limits = limits_payload(group, user=user)
    equipment = allowed_equipment(group)
    return {
        'limited': limits is not None,
        'limits': limits,
        'equipment': equipment,
        'can_change_privileged': can_change_privileged(user),
    }


def validate_workspace_resources(user: User, *, cpu, ram, gpu) -> str | None:
    group = get_user_group(user)
    if group is None:
        return None
    try:
        cpu_val = parse_cpu_value(cpu)
    except ValueError:
        return 'invalid cpu'
    if cpu_val > float(group.max_cpu):
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


def validate_server_count(user: User) -> str | None:
    group = get_user_group(user)
    if group is None or not group.max_servers:
        return None
    current = user_server_count(user)
    if current >= group.max_servers:
        return f'Server count exceeds group limit ({group.max_servers} max, you have {current})'
    return None


def validate_drive_count(user: User) -> str | None:
    group = get_user_group(user)
    if group is None or not group.max_drives:
        return None
    current = user_drive_count(user)
    if current >= group.max_drives:
        return f'Drive count exceeds group limit ({group.max_drives} max, you have {current})'
    return None
