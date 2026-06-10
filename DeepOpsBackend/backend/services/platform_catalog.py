"""Platform-wide equipment options and server plan templates."""

from __future__ import annotations

from backend.models import PlatformEquipmentOption, ServerPlanTemplate

FALLBACK_CPU = [2.0, 4.0, 8.0, 16.0, 32.0]


def parse_cpu_value(value) -> float:
    if value is None or value == '':
        raise ValueError('invalid cpu')
    try:
        cpu = float(value)
    except (TypeError, ValueError):
        raise ValueError(f'invalid cpu: {value!r}')
    if cpu <= 0:
        raise ValueError(f'invalid cpu: {value!r}')
    return cpu
FALLBACK_RAM = ['2G', '4G', '8G', '16G', '32G', '64G']
# GPU values: "count" or "count:gpumem_mib" (nvidia.com/gpu + nvidia.com/gpumem)
FALLBACK_GPU = ['none', '1:1024', '1:10240', '1:40960', '2:20480']
FALLBACK_DRIVE_SIZES = ['20Gi', '50Gi', '100Gi', '200Gi', '500Gi', '1Ti']
FALLBACK_GPU_VRAM = {
    'none': 0,
    '': 0,
    '1:1024': 1,
    '1:10240': 10,
    '1:40960': 40,
    '2:20480': 40,
    # Legacy values (still spawn correctly via gpu_resources.py)
    'mig-2g.10gb': 10,
    'mig-3g.20gb': 20,
    'gpu': 40,
    'gpu:2': 80,
}


def _option_values(category: str, *, active_only: bool = True) -> list:
    qs = PlatformEquipmentOption.objects.filter(category=category)
    if active_only:
        qs = qs.filter(is_active=True)
    return [row.value for row in qs.order_by('sort_order', 'value')]


def all_cpu(*, active_only: bool = True) -> list[float]:
    values = _option_values(PlatformEquipmentOption.CATEGORY_CPU, active_only=active_only)
    if not values:
        return FALLBACK_CPU[:]
    cpus: list[float] = []
    for value in values:
        try:
            cpus.append(parse_cpu_value(value))
        except ValueError:
            continue
    return cpus or FALLBACK_CPU[:]


def all_ram(*, active_only: bool = True) -> list[str]:
    values = _option_values(PlatformEquipmentOption.CATEGORY_RAM, active_only=active_only)
    return values or FALLBACK_RAM[:]


def all_gpu(*, active_only: bool = True) -> list[str]:
    values = _option_values(PlatformEquipmentOption.CATEGORY_GPU, active_only=active_only)
    return values or FALLBACK_GPU[:]


def all_drive_sizes(*, active_only: bool = True) -> list[str]:
    values = _option_values(PlatformEquipmentOption.CATEGORY_DRIVE_SIZE, active_only=active_only)
    return values or FALLBACK_DRIVE_SIZES[:]


def get_gpu_vram_map(*, active_only: bool = True) -> dict[str, int]:
    qs = PlatformEquipmentOption.objects.filter(category=PlatformEquipmentOption.CATEGORY_GPU)
    if active_only:
        qs = qs.filter(is_active=True)
    mapping = dict(FALLBACK_GPU_VRAM)
    for row in qs:
        mapping[row.value] = row.vram_g
    return mapping


def equipment_payload(*, active_only: bool = True) -> dict:
    return {
        'cpu': all_cpu(active_only=active_only),
        'ram': all_ram(active_only=active_only),
        'gpu': all_gpu(active_only=active_only),
        'drive_sizes': all_drive_sizes(active_only=active_only),
    }


def _template_payload(template: ServerPlanTemplate) -> dict:
    return {
        'id': template.id,
        'name': template.name,
        'image': template.image,
        'cpu': template.cpu,
        'ram': template.ram,
        'gpu': template.gpu or 'none',
        'docker_repository': template.docker_repository or '',
        'docker_tag': template.docker_tag or '',
        'exposed_ports': template.exposed_ports or [8080],
        'container_command': template.container_command or [],
        'env_defaults': template.env_defaults or {},
        'sort_order': template.sort_order,
        'is_active': template.is_active,
    }


def plan_templates(*, active_only: bool = True) -> list[dict]:
    qs = ServerPlanTemplate.objects.all()
    if active_only:
        qs = qs.filter(is_active=True)
    return [_template_payload(t) for t in qs.order_by('sort_order', 'name')]


def catalog_payload(*, active_only: bool = True) -> dict:
    return {
        'equipment': equipment_payload(active_only=active_only),
        'templates': plan_templates(active_only=active_only),
    }


def _option_payload(option: PlatformEquipmentOption) -> dict:
    return {
        'id': option.id,
        'category': option.category,
        'value': option.value,
        'vram_g': option.vram_g,
        'sort_order': option.sort_order,
        'is_active': option.is_active,
    }


def admin_catalog_payload() -> dict:
    options = [
        _option_payload(row)
        for row in PlatformEquipmentOption.objects.order_by('category', 'sort_order', 'value')
    ]
    templates = [
        _template_payload(row)
        for row in ServerPlanTemplate.objects.order_by('sort_order', 'name')
    ]
    return {
        'equipment': equipment_payload(active_only=False),
        'templates': templates,
        'options': options,
    }
