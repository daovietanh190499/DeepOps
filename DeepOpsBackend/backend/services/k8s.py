import json
import os
import subprocess

from .config import get_hub_config
from .gpu_resources import parse_gpu_resources
from .k8s_env import CODEHUB_CHART_PATH, DEFAULT_PORT, DOMAIN_NAME, NAMESPACE
from .ssh_keys import get_or_none, ssh_secret_name


def _storage_class() -> str:
    return get_hub_config().get('storage', {}).get('storageClassName', 'directpv-min-io')


def _ingress_settings() -> dict:
    ingress = get_hub_config().get('ingress') or {}
    if not isinstance(ingress, dict):
        ingress = {}
    controller = str(ingress.get('controller') or 'both').strip().lower()
    if controller not in ('auto', 'nginx', 'traefik', 'both'):
        controller = 'both'
    class_name = str(ingress.get('className') or 'nginx').strip() or 'nginx'
    return {'controller': controller, 'className': class_name}


def _ingress_uses_nginx() -> bool:
    controller = _ingress_settings()['controller']
    return controller in ('nginx', 'both')


def _ingress_helm_flags() -> list[str]:
    settings = _ingress_settings()
    flags = [
        '--set', 'ingress.enabled=true',
        '--set-string', f'ingress.controller={settings["controller"]}',
        '--set', f'ingress.className={settings["className"]}',
    ]
    if _ingress_uses_nginx():
        flags.extend([
            '--set-string', 'ingress.annotations.nginx\\.ingress\\.kubernetes\\.io/proxy-body-size=0',
            '--set-string', 'ingress.annotations.nginx\\.ingress\\.kubernetes\\.io/proxy-read-timeout=600',
            '--set-string', 'ingress.annotations.nginx\\.ingress\\.kubernetes\\.io/proxy-send-timeout=600',
            '--set-string', 'ingress.annotations.nginx\\.ingress\\.kubernetes\\.io/proxy-buffering=off',
            '--set-string', 'ingress.annotations.nginx\\.ingress\\.kubernetes\\.io/proxy-http-version=1.1',
        ])
    return flags


def _helm_release_status(release_name: str) -> str | None:
    """Return helm release status, or None if the release name is not reserved."""
    result = subprocess.run(
        ['helm', 'list', '-n', NAMESPACE, '-a', '-o', 'json'],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not (result.stdout or '').strip():
        return None
    try:
        releases = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    for item in releases:
        if (item.get('name') or '').strip() == release_name:
            return (item.get('status') or '').strip().lower() or None
    return None


def _clear_stuck_helm_release(release_name: str) -> tuple[str, int]:
    """Remove failed/stuck helm metadata so upgrade --install can proceed."""
    status = _helm_release_status(release_name)
    if status is None or status == 'deployed':
        return '', 0
    result = subprocess.run(
        ['helm', 'uninstall', release_name, '-n', NAMESPACE],
        capture_output=True,
        text=True,
        check=False,
    )
    logs = ((result.stdout or '') + (result.stderr or '')).strip()
    if result.returncode != 0 and 'not found' not in logs.lower():
        return logs or 'helm uninstall failed', result.returncode
    return logs or f'cleared helm release in {status!r} state', 0


def build_spawn_config(workspace) -> dict:
    from .workspace_mounts import build_pvc_volume_specs, spawn_drive_mounts

    gpu_spec = parse_gpu_resources(workspace.gpu)
    ram_str = str(workspace.ram)
    ram_value = int(ram_str[:-1]) if ram_str.endswith('G') else int(ram_str)

    ports_raw = workspace.exposed_ports or []
    ports = [int(p) for p in ports_raw] if ports_raw else [int(DEFAULT_PORT)]
    main_port = ports[0]
    extra_ports = ports[1:]

    user = workspace.user
    slug = workspace.slug
    mount_entries = spawn_drive_mounts(workspace)
    pvc_volumes, pvc_volume_mounts = build_pvc_volume_specs(mount_entries)
    ssh_record = get_or_none(workspace)

    return {
        'workspace_id': str(workspace.id),
        'username': user.username,
        'slug': slug,
        'release_name': workspace.release_name,
        'hostname': workspace.hostname,
        'cpu': workspace.cpu,
        'max_cpu': workspace.cpu * 1.5,
        'max_ram': f'{int(ram_value * 1.5)}G',
        'ram': workspace.ram,
        'gpu_enabled': gpu_spec['enabled'],
        'gpu_count': gpu_spec['count'],
        'gpu_memory_mib': gpu_spec['memory_mib'],
        'image': workspace.docker_repository,
        'image_tag': workspace.docker_tag,
        'defaultPort': main_port,
        'extra_ports': extra_ports,
        'env_vars': dict(workspace.env_vars or {}),
        'container_command': list(workspace.container_command or []),
        'storage_class': _storage_class(),
        'pvc_volumes': pvc_volumes,
        'pvc_volume_mounts': pvc_volume_mounts,
        'secret_name': f'{user.username}-{slug}-secret',
        'ssh_enabled': ssh_record is not None,
        'ssh_secret_name': ssh_secret_name(workspace),
        'ssh_public_key': ssh_record.public_key if ssh_record else '',
        'ws_tunnel_ports': list(workspace.ws_tunnel_ports or []) if isinstance(workspace.ws_tunnel_ports, list) else [],
        'privileged': workspace.privileged,
    }


def _security_context_helm_flags(privileged: bool) -> list[str]:
    if privileged:
        return [
            '--set', 'securityContext.privileged=true',
            '--set', 'securityContext.runAsUser=0',
            '--set', 'securityContext.allowPrivilegeEscalation=true',
            '--set', 'securityContext.capabilities.add[0]=SYS_ADMIN',
        ]
    return [
        '--set-json',
        'securityContext={"runAsUser":1000,"allowPrivilegeEscalation":false,"privileged":false}',
    ]


def _sidecar_ingress_flags(config: dict) -> list[str]:
    """Path-based SSH / port-tunnel routes on the hub domain."""
    ssh_on = config.get('ssh_enabled') and config.get('ssh_secret_name')
    tunnel_on = bool(config.get('ws_tunnel_ports'))
    if not ssh_on and not tunnel_on:
        return []

    username = config['username']
    slug = config['slug']
    flags = [
        '--set', 'sidecarIngress.enabled=true',
        '--set-string', f'sidecarIngress.host={DOMAIN_NAME}',
        '--set-string', f'sidecarIngress.tlsSecretName=tls-{NAMESPACE}-secret',
    ]
    if ssh_on:
        flags.extend(['--set-string', f'sshBridge.ingressPath=/{username}/{slug}/ssh-tunnel'])
    if tunnel_on:
        flags.extend(['--set-string', f'portTunnel.ingressPath=/{username}/{slug}/port-tunnel'])
    return flags


def _parse_memory_bytes(ram_str: str) -> int:
    s = str(ram_str).strip()
    if not s:
        return 0
    if s.endswith('Gi'):
        return int(float(s[:-2]) * 1024 ** 3)
    if s.endswith('G'):
        return int(float(s[:-1]) * 1024 ** 3)
    if s.endswith('Mi'):
        return int(float(s[:-2]) * 1024 ** 2)
    if s.endswith('M'):
        return int(float(s[:-1]) * 1024 ** 2)
    if s.endswith('Ki'):
        return int(float(s[:-2]) * 1024)
    try:
        return int(s)
    except ValueError:
        return 4294967296


def _helm_base_cmd(config: dict) -> list[str]:
    gpu_flags: list[str] = []
    if config.get('gpu_enabled'):
        gpu_flags = [
            '--set', 'gpu.enabled=true',
            '--set', f'gpu.count={config["gpu_count"]}',
        ]
        if config.get('gpu_memory_mib', 0) > 0:
            gpu_flags.extend(['--set', f'gpu.memoryMiB={config["gpu_memory_mib"]}'])

    cmd = [
        'helm', 'upgrade', '--install', '--create-namespace',
        '-n', NAMESPACE,
        '--set-string', f'image.repository={config["image"]}',
        '--set', 'image.pullPolicy=IfNotPresent',
        '--set-string', f'image.tag={config["image_tag"]}',
        '--set', f'podLabels.{NAMESPACE}-username={config["username"]}',
        '--set', f'podLabels.{NAMESPACE}-workspace={config["slug"]}',
        '--set', f'podLabels.{NAMESPACE}-workspace-id={config["workspace_id"]}',
        '--set', f'secret.name={config["secret_name"]}',
        '--set', 'serviceAccount.create=false',
        '--set', 'serviceAccount.automount=false',
        '--set', 'serviceAccount.name=default',
        '--set', 'podSecurityContext.fsGroup=100',
        *_security_context_helm_flags(config.get('privileged', False)),
        '--set', 'service.type=ClusterIP',
        '--set', f'service.port={config["defaultPort"]}',
        *_ingress_helm_flags(),
        '--set', f'ingress.hosts[0].host={config["hostname"]}',
        '--set', 'ingress.hosts[0].paths[0].path=/',
        '--set', 'ingress.hosts[0].paths[0].pathType=Prefix',
        '--set', f'ingress.tls[0].secretName=tls-{NAMESPACE}-secret',
        '--set', f'ingress.tls[0].hosts[0]={config["hostname"]}',
        '--set', f'resources.limits.cpu={config["max_cpu"]}',
        '--set', f'resources.limits.memory={config["max_ram"]}',
        '--set', f'resources.requests.cpu={config["cpu"]}',
        '--set', f'resources.requests.memory={config["ram"]}',
    ]

    pvc_volumes = config.get('pvc_volumes') or []
    pvc_volume_mounts = config.get('pvc_volume_mounts') or []
    if pvc_volumes:
        cmd.extend(['--set', 'persistence.enabled=false'])
    else:
        cmd.extend(['--set', 'persistence.enabled=false'])

    if config.get('replica_count') is not None:
        cmd.extend(['--set', f'replicaCount={int(config["replica_count"])}'])

    env_vars = dict(config.get('env_vars', {}))
    if env_vars.get('password'):
        env_vars['PASSWORD'] = env_vars.pop('password')
    has_auth = False
    for key in ('PASSWORD', 'HASHED_PASSWORD'):
        if env_vars.get(key):
            cmd.extend(['--set-string', f'env.secret.{key}={env_vars.pop(key)}'])
            has_auth = True
    if has_auth:
        cmd.extend(['--set', 'auth.resetConfigOnDeploy=true'])
        if pvc_volume_mounts:
            first_mount = pvc_volume_mounts[0]
            cmd.extend([
                '--set-string', f'auth.resetVolumeName={first_mount["name"]}',
                '--set-string', f'auth.resetMountPath={first_mount["mountPath"]}',
            ])
            if first_mount.get('subPath'):
                cmd.extend(['--set-string', f'auth.resetSubPath={first_mount["subPath"]}'])

    env_list = [{'name': k, 'value': str(v)} for k, v in env_vars.items()]
    if env_list:
        cmd.extend(['--set-json', f'extraEnv={json.dumps(env_list)}'])

    for i, port in enumerate(config.get('extra_ports', [])):
        name = f'port-{port}'
        cmd.extend([
            '--set', f'service.extraPorts[{i}].port={port}',
            '--set', f'service.extraPorts[{i}].name={name}',
        ])

    command = config.get('container_command') or []
    if command:
        cmd.extend(['--set-json', f'container.command={json.dumps(command)}'])

    volumes = [{'name': 'shm-volume', 'emptyDir': {'medium': 'Memory'}}] + pvc_volumes
    volume_mounts = [{'name': 'shm-volume', 'mountPath': '/dev/shm'}] + pvc_volume_mounts
    cmd.extend(['--set-json', f'volumes={json.dumps(volumes)}'])
    cmd.extend(['--set-json', f'volumeMounts={json.dumps(volume_mounts)}'])

    if config.get('ssh_enabled') and config.get('ssh_secret_name'):
        bridge_image = os.environ.get('SSH_BRIDGE_IMAGE', 'localhost:32000/ssh-bridge')
        bridge_tag = os.environ.get('SSH_BRIDGE_TAG', 'latest')
        cmd.extend([
            '--set', 'sshBridge.enabled=true',
            '--set', 'sshBridge.rbac.create=true',
            '--set-string', f'sshBridge.secretName={config["ssh_secret_name"]}',
            '--set-string', f'sshBridge.image.repository={bridge_image}',
            '--set-string', f'sshBridge.image.tag={bridge_tag}',
        ])

    monitor_image = os.environ.get('MONITOR_SIDECAR_IMAGE', 'localhost:32000/monitor-sidecar')
    monitor_tag = os.environ.get('MONITOR_SIDECAR_TAG', 'latest')
    max_cpu = config.get('max_cpu', config['cpu'] * 1.5)
    cpu_limit_m = int(float(max_cpu) * 1000)
    mem_limit_b = _parse_memory_bytes(config.get('max_ram', config['ram']))
    cmd.extend([
        '--set', 'monitor.enabled=true',
        '--set', 'monitor.rbac.create=true',
        '--set-string', f'monitor.image.repository={monitor_image}',
        '--set-string', f'monitor.image.tag={monitor_tag}',
        '--set-string', f'monitor.cpuLimitMillicores={cpu_limit_m}',
        '--set-string', f'monitor.memoryLimitBytes={mem_limit_b}',
    ])

    tunnel_ports = config.get('ws_tunnel_ports') or []
    if tunnel_ports:
        port_tunnel_image = os.environ.get('PORT_TUNNEL_IMAGE', 'localhost:32000/port-tunnel')
        port_tunnel_tag = os.environ.get('PORT_TUNNEL_TAG', 'latest')
        cmd.extend([
            '--set', 'portTunnel.enabled=true',
            '--set-json', f'portTunnel.ports={json.dumps([int(p) for p in tunnel_ports])}',
            '--set-string', f'portTunnel.image.repository={port_tunnel_image}',
            '--set-string', f'portTunnel.image.tag={port_tunnel_tag}',
        ])

    cmd.extend([
        *_sidecar_ingress_flags(config),
        *gpu_flags,
        config['release_name'],
        CODEHUB_CHART_PATH,
    ])
    return cmd


def _delete_workspace_deployments(release_name: str) -> tuple[str, int]:
    """Remove existing workspace deployment(s) so a fresh pod can be created."""
    result = subprocess.run(
        [
            'kubectl', 'delete', 'deployment',
            '-n', NAMESPACE,
            f'-l=app.kubernetes.io/instance={release_name}',
            '--ignore-not-found=true',
            '--wait=true',
            '--timeout=120s',
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    logs = ((result.stdout or '') + (result.stderr or '')).strip()
    if result.returncode != 0:
        return logs or 'deployment delete failed', result.returncode
    return logs or 'deployment removed', 0


def create_codehub(config: dict) -> tuple[str, str, int]:
    if config.get('ssh_enabled'):
        from backend.models import Workspace
        from .ssh_k8s import sync_ssh_secret_for_workspace

        workspace = Workspace.objects.get(id=config['workspace_id'])
        logs, code = sync_ssh_secret_for_workspace(workspace)
        if code != 0:
            return '', f'ssh secret apply failed: {logs}', code
        del_logs, del_code = _delete_workspace_deployments(config['release_name'])
        if del_code != 0:
            return '', f'deployment cleanup failed: {del_logs}', del_code
    prep_logs, prep_code = _clear_stuck_helm_release(config['release_name'])
    if prep_code != 0:
        return '', f'helm release cleanup failed: {prep_logs}', prep_code
    cmd = _helm_base_cmd(config)
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    logs = result.stdout + result.stderr
    return ' '.join(cmd), logs, result.returncode


def scale_codehub(release_name: str, replicas: int) -> tuple[str, int]:
    """Scale the workspace deployment without removing the Helm release."""
    lookup = subprocess.run(
        [
            'kubectl', 'get', 'deployment',
            '-n', NAMESPACE,
            f'-l=app.kubernetes.io/instance={release_name}',
            '-o', 'json',
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if lookup.returncode != 0 or not (lookup.stdout or '').strip():
        return 'deployment lookup failed', 1
    try:
        data = json.loads(lookup.stdout)
    except json.JSONDecodeError:
        return 'deployment lookup failed', 1

    items = data.get('items') or []
    if not items:
        return ('', 0) if replicas == 0 else ('deployment not found', 1)

    logs_parts: list[str] = []
    exit_code = 0
    patch_body = json.dumps({'spec': {'replicas': replicas}})
    for item in items:
        name = (item.get('metadata') or {}).get('name', '')
        if not name:
            continue
        result = subprocess.run(
            [
                'kubectl', 'patch', 'deployment', name,
                '-n', NAMESPACE,
                '--type=merge',
                '-p', patch_body,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        chunk = ((result.stdout or '') + (result.stderr or '')).strip()
        if chunk:
            logs_parts.append(chunk)
        if result.returncode != 0:
            exit_code = result.returncode

    return '\n'.join(logs_parts) or 'ok', exit_code


def stop_codehub(release_name: str) -> tuple[str, int]:
    return scale_codehub(release_name, 0)


def remove_codehub(release_name: str) -> int:
    """Remove a workspace Helm release. No-op if the release does not exist."""
    if _helm_release_status(release_name) is None:
        return 0
    return subprocess.call([
        'helm', 'uninstall', '-n', NAMESPACE, release_name,
    ])


def get_codehub_workspace(workspace) -> dict:
    result = subprocess.run(
        [
            'kubectl', 'get', 'pod',
            f'-l={NAMESPACE}-workspace-id={workspace.id}',
            '-n', NAMESPACE,
            '-o', 'json',
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if not result.stdout.strip():
        return {'items': [], 'apiVersion': 'v1', 'kind': 'List'}
    return json.loads(result.stdout)
