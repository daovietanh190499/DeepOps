import json
import os
import subprocess

from .config import get_hub_config
from .gpu_resources import parse_gpu_resources
from .k8s_env import CODEHUB_CHART_PATH, DEFAULT_PORT, DOMAIN_NAME, NAMESPACE
from .ssh_keys import get_or_none, ssh_secret_name


def _storage_class() -> str:
    return get_hub_config().get('storage', {}).get('storageClassName', 'directpv-min-io')


def build_spawn_config(workspace) -> dict:
    from .workspace_mounts import spawn_drive_mounts

    gpu_spec = parse_gpu_resources(workspace.gpu)
    ram_str = str(workspace.ram)
    ram_value = int(ram_str[:-1]) if ram_str.endswith('G') else int(ram_str)

    ports_raw = workspace.exposed_ports or []
    ports = [int(p) for p in ports_raw] if ports_raw else [int(DEFAULT_PORT)]
    main_port = ports[0]
    extra_ports = ports[1:]

    user = workspace.user
    slug = workspace.slug
    mounts = spawn_drive_mounts(workspace)
    if not mounts:
        raise ValueError('workspace has no drive assigned')

    primary = mounts[0]
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
        'claim_name': primary['claim_name'],
        'mount_path': primary['mount_path'],
        'extra_mounts': mounts[1:],
        'secret_name': f'{user.username}-{slug}-secret',
        'ssh_enabled': ssh_record is not None,
        'ssh_secret_name': ssh_secret_name(workspace),
        'ssh_public_key': ssh_record.public_key if ssh_record else '',
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
        '--set', f'resources.limits.cpu={config["max_cpu"]}',
        '--set', f'resources.limits.memory={config["max_ram"]}',
        '--set', f'resources.requests.cpu={config["cpu"]}',
        '--set', f'resources.requests.memory={config["ram"]}',
    ]

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

    volumes = [{'name': 'shm-volume', 'emptyDir': {'medium': 'Memory'}}]
    volume_mounts = [{'name': 'shm-volume', 'mountPath': '/dev/shm'}]
    for extra in config.get('extra_mounts') or []:
        volumes.append({
            'name': extra['volume_name'],
            'persistentVolumeClaim': {'claimName': extra['claim_name']},
        })
        volume_mounts.append({
            'name': extra['volume_name'],
            'mountPath': extra['mount_path'],
        })
    cmd.extend(['--set-json', f'volumes={json.dumps(volumes)}'])
    cmd.extend(['--set-json', f'volumeMounts={json.dumps(volume_mounts)}'])

    if config.get('ssh_enabled') and config.get('ssh_secret_name'):
        bridge_image = os.environ.get('SSH_BRIDGE_IMAGE', 'localhost:32000/ssh-bridge')
        bridge_tag = os.environ.get('SSH_BRIDGE_TAG', 'latest')
        cmd.extend([
            '--set', 'sshBridge.enabled=true',
            '--set', 'sshBridge.serviceAccount.create=true',
            '--set', 'sshBridge.rbac.create=true',
            '--set-string', f'sshBridge.secretName={config["ssh_secret_name"]}',
            '--set-string', f'sshBridge.image.repository={bridge_image}',
            '--set-string', f'sshBridge.image.tag={bridge_tag}',
        ])

    cmd.extend([
        *gpu_flags,
        config['release_name'],
        CODEHUB_CHART_PATH,
    ])
    return cmd


def create_codehub(config: dict) -> tuple[str, str, int]:
    if config.get('ssh_enabled'):
        from backend.models import Workspace
        from .ssh_k8s import sync_ssh_secret_for_workspace

        workspace = Workspace.objects.get(id=config['workspace_id'])
        logs, code = sync_ssh_secret_for_workspace(workspace)
        if code != 0:
            return '', f'ssh secret apply failed: {logs}', code
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
    from .k8s_status import helm_release_exists

    if not helm_release_exists(release_name):
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
