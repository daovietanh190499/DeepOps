import os
import json
import subprocess

DEFAULT_SPAWNER = os.environ.get('SPAWNER', 'k8s')
NAMESPACE = os.environ.get('NAMESPACE', 'dohub')

def create_codehub(config):
    subprocess.run([
        f"helm upgrade --install --create-namespace -n {NAMESPACE}",
        f'--set "image.repository={config['image']}"',,
        f'--set "image.repository={config['image']}"',
        '--set "image.pullPolicy=Always"',
        '--set "image.tag=latest"',
        f'--set "podLabels.{NAMESPACE}-username={config['username']}"',
        f'--set "secret.name={config['username']}-secret"',
        f'--set "env.secret.PASSWORD={config['password']}"',
        '--set "serviceAccount.enable=false"',
        '--set "serviceAccount.automount=false"',
        '--set "serviceAccount.name=default"',
        '--set "podSecurityContext.fsGroup=100"',
        '--set "securityContext.capabilities.add[0]=SYS_ADMIN"',
        '--set "securityContext.allowPrivilegeEscalation=true"',
        '--set "securityContext.runAsUser=0"',
        '--set "service.type=ClusterIP"',
        f'--set "service.port={config['defaultPort']}"',
        '--set "ingress.enabled=true"',
        '--set "ingress.className=nginx"',
        f'--set "ingress.hosts[0].host={config['username']}.vkist-hub.com"',
        '--set "ingress.hosts[0].paths[0].path=/"',
        '--set "ingress.hosts[0].paths[0].pathType=Prefix"',
        f'--set "ingress.tls[0].secretName=tls-{NAMESPACE}-secret"',
        f'--set "ingress.tls[0].hosts[0]={config['username']}.vkist-hub.com"',
        f'--set "mainVolume.claimName=claim-{NAMESPACE}-{config['username']}"',
        f'--set "mainVolume.dataPath='{config['path'] + '/dohub-' + config['username']}'"',
        '--set "volumes[0].name=shm-volume"',
        '--set "volumes[0].emptyDir.medium=Memory"',
        f'--set "volumes[1].name=volume-{config['username']}"',
        f'--set "volumes[1].persistentVolumeClaim.claimName=claim-{NAMESPACE}-{config['username']}"',
        '--set "volumeMounts[0].mountPath=/dev/shm"',
        '--set "volumeMounts[0].name=shm-volume"',
        '--set "volumeMounts[1].mountPath=/home/coder"',
        f'--set "volumeMounts[1].name=volume-{config['username']}"',
        f'--set "resources.limits.cpu={config['max_cpu']}"',
        f'--set "resources.limits.memory={config['max_ram']}"',
        f'--set "resources.limits.{config['gpu_type'].replace('.', '\.')}={config['gpu_quantity']}"',
        f'--set "resources.requests.cpu={config['cpu']}"',
        f'--set "resources.requests.memory={config['ram']}"',
        f'--set "resources.requests.{config['gpu_type'].replace('.', '\.')}={config['gpu_quantity']}"',
        f'{NAMESPACE}-{config['username']} spawners/k8s/codehub'
    ])

def remove_codehub(config):
    os.system(
        f"""helm uninstall -n {NAMESPACE} {NAMESPACE}-{config['username']} spawners/k8s/codehub"""
    )

def get_codehub(username):
    result = os.popen(f"kubectl get pod -l={NAMESPACE}-username={username} -n {NAMESPACE} -o json").read()
    result = json.loads(result)
    return result
