import json
import os
import subprocess

from .config import get_hub_config

NAMESPACE = os.environ.get('NAMESPACE', 'dohub')
DOMAIN_NAME = os.environ.get('DOMAIN_NAME', 'dohub.com')
DEFAULT_PORT = os.environ.get('DEFAULT_PORT', '8080')
CODEHUB_CHART_PATH = os.environ.get(
    'CODEHUB_CHART_PATH',
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', '..', '..', 'charts', 'codehub')
    ),
)


def _storage_class() -> str:
    return get_hub_config().get('storage', {}).get('storageClassName', 'directpv-min-io')


def build_spawn_config(workspace) -> dict:
    gpu = workspace.gpu or ''
    not_use_gpu = not gpu or gpu in ('null', 'none', '')
    gpu_type = 'nvidia.com/' + (gpu.split(':')[0] if ':' in gpu else gpu)
    gpu_quantity = int(gpu.split(':')[1]) if ':' in gpu else 1
    ram_str = str(workspace.ram)
    ram_value = int(ram_str[:-1]) if ram_str.endswith('G') else int(ram_str)

    ports_raw = workspace.exposed_ports or []
    ports = [int(p) for p in ports_raw] if ports_raw else [int(DEFAULT_PORT)]
    main_port = ports[0]
    extra_ports = ports[1:]

    user = workspace.user
    slug = workspace.slug
    drive = workspace.user_drive
    if not drive:
        raise ValueError('workspace has no drive assigned')

    mount_path = (workspace.mount_path or '/home/coder').strip() or '/home/coder'

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
        'gpu_type': gpu_type,
        'gpu_quantity': gpu_quantity,
        'not_use_gpu': not_use_gpu,
        'image': workspace.docker_repository,
        'image_tag': workspace.docker_tag,
        'defaultPort': main_port,
        'extra_ports': extra_ports,
        'env_vars': dict(workspace.env_vars or {}),
        'container_command': list(workspace.container_command or []),
        'storage_class': _storage_class(),
        'claim_name': drive.claim_name,
        'mount_path': mount_path,
        'secret_name': f'{user.username}-{slug}-secret',
    }


def _helm_base_cmd(config: dict) -> list[str]:
    gpu_flags: list[str] = []
    if not config['not_use_gpu']:
        gpu_key = config['gpu_type']
        gpu_flags = [
            '--set', f'resources.limits.{gpu_key}={config["gpu_quantity"]}',
            '--set', f'resources.requests.{gpu_key}={config["gpu_quantity"]}',
        ]

    cmd = [
        'helm', 'upgrade', '--install', '--create-namespace',
        '-n', NAMESPACE,
        '--set', f'image.repository={config["image"]}',
        '--set', 'image.pullPolicy=IfNotPresent',
        '--set', f'image.tag={config["image_tag"]}',
        '--set', f'podLabels.{NAMESPACE}-username={config["username"]}',
        '--set', f'podLabels.{NAMESPACE}-workspace={config["slug"]}',
        '--set', f'podLabels.{NAMESPACE}-workspace-id={config["workspace_id"]}',
        '--set', f'secret.name={config["secret_name"]}',
        '--set', 'serviceAccount.create=false',
        '--set', 'serviceAccount.automount=false',
        '--set', 'serviceAccount.name=default',
        '--set', 'podSecurityContext.fsGroup=100',
        '--set', 'securityContext.capabilities.add[0]=SYS_ADMIN',
        '--set', 'securityContext.allowPrivilegeEscalation=true',
        '--set', 'securityContext.runAsUser=0',
        '--set', 'service.type=ClusterIP',
        '--set', f'service.port={config["defaultPort"]}',
        '--set', 'ingress.enabled=true',
        '--set-string', 'ingress.annotations.nginx\\.ingress\\.kubernetes\\.io/proxy-body-size=0',
        '--set-string', 'ingress.annotations.nginx\\.ingress\\.kubernetes\\.io/proxy-read-timeout=600',
        '--set-string', 'ingress.annotations.nginx\\.ingress\\.kubernetes\\.io/proxy-send-timeout=600',
        '--set-string', 'ingress.annotations.nginx\\.ingress\\.kubernetes\\.io/proxy-buffering=off',
        '--set-string', 'ingress.annotations.nginx\\.ingress\\.kubernetes\\.io/proxy-http-version=1.1',
        '--set', 'ingress.className=nginx',
        '--set', f'ingress.hosts[0].host={config["hostname"]}',
        '--set', 'ingress.hosts[0].paths[0].path=/',
        '--set', 'ingress.hosts[0].paths[0].pathType=Prefix',
        '--set', f'ingress.tls[0].secretName=tls-{NAMESPACE}-secret',
        '--set', f'ingress.tls[0].hosts[0]={config["hostname"]}',
        '--set', 'persistence.enabled=true',
        '--set', 'persistence.createPvc=false',
        '--set', f'persistence.claimName={config["claim_name"]}',
        '--set', f'mainVolume.claimName={config["claim_name"]}',
        '--set', f'persistence.mountPath={config["mount_path"]}',
        '--set', 'volumes[0].name=shm-volume',
        '--set', 'volumes[0].emptyDir.medium=Memory',
        '--set', f'resources.limits.cpu={config["max_cpu"]}',
        '--set', f'resources.limits.memory={config["max_ram"]}',
        '--set', f'resources.requests.cpu={config["cpu"]}',
        '--set', f'resources.requests.memory={config["ram"]}',
    ]

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

    cmd.extend([
        *gpu_flags,
        config['release_name'],
        CODEHUB_CHART_PATH,
    ])
    return cmd


def create_codehub(config: dict) -> tuple[str, str, int]:
    cmd = _helm_base_cmd(config)
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    logs = result.stdout + result.stderr
    return ' '.join(cmd), logs, result.returncode


def remove_codehub(release_name: str) -> int:
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
