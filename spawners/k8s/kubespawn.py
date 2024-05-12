import os
import json

DEFAULT_SPAWNER = os.environ.get('SPAWNER', 'k8s')
NAMESPACE = os.environ.get('NAMESPACE', 'dohub')

def create_codehub(config):
    backslash = "\\"
    os.system(
        f""" helm upgrade --install --create-namespace -n {NAMESPACE} {backslash}
            --set "image.repository={config['image']}" {backslash}
            --set "image.pullPolicy=Always" {backslash}
            --set "image.tag=latest" {backslash}
            --set "podLabels.{NAMESPACE}-username={config['username']}" {backslash}
            --set "secret.name={config['username']}-secret" {backslash}
            --set "env.secret.PASSWORD={config['password']}" {backslash}
            --set "serviceAccount.enable=false" {backslash}
            --set "serviceAccount.automount=false" {backslash}
            --set "serviceAccount.name=default" {backslash}
            --set "podSecurityContext.fsGroup=100" {backslash}
            --set "securityContext.capabilities.add[0]=SYS_ADMIN" {backslash}
            --set "securityContext.allowPrivilegeEscalation=true" {backslash}
            --set "securityContext.runAsUser=0" {backslash}
            --set "service.type=ClusterIP" {backslash}
            --set "service.port={config['defaultPort']}" {backslash}
            --set "ingress.enabled=true" {backslash}
            --set "ingress.className=nginx" {backslash}
            --set "ingress.hosts[0].host={config['username']}.vkist-hub.com" {backslash}
            --set "ingress.hosts[0].paths[0].path=/" {backslash}
            --set "ingress.hosts[0].paths[0].pathType=Prefix" {backslash}
            --set "ingress.tls[0].secretName=tls-{NAMESPACE}-secret" {backslash}
            --set "ingress.tls[0].hosts[0]={config['username']}.vkist-hub.com" {backslash}
            --set "mainVolume.claimName=claim-{NAMESPACE}-{config['username']}" {backslash}
            --set "mainVolume.dataPath='{config['path'] + '/dohub-' + config['username']}'" {backslash}
            --set "volumes[0].name=shm-volume" {backslash}
            --set "volumes[0].emptyDir.medium=Memory" {backslash}
            --set "volumes[1].name=volume-{config['username']}" {backslash}
            --set "volumes[1].persistentVolumeClaim.claimName=claim-{NAMESPACE}-{config['username']}" {backslash}
            --set "volumeMounts[0].mountPath=/dev/shm" {backslash}
            --set "volumeMounts[0].name=shm-volume" {backslash}
            --set "volumeMounts[1].mountPath=/home/coder" {backslash}
            --set "volumeMounts[1].name=volume-{config['username']}" {backslash}
            --set "resources.limits.cpu={config['max_cpu']}" {backslash}
            --set "resources.limits.memory={config['max_ram']}" {backslash}
            --set "resources.limits.{config['gpu_type'].replace('.', '\.')}={config['gpu_quantity']}" {backslash}
            --set "resources.requests.cpu={config['cpu']}" {backslash}
            --set "resources.requests.memory={config['ram']}" {backslash}
            --set "resources.requests.{config['gpu_type'].replace('.', '\.')}={config['gpu_quantity']}" {backslash}
            {NAMESPACE}-{config['username']} spawners/k8s/codehub
        """
    )

def remove_codehub(config):
    os.system(
        f"""helm uninstall -n {NAMESPACE} {NAMESPACE}-{config['username']} spawners/k8s/codehub"""
    )

def get_codehub(username):
    result = os.popen(f"kubectl get pod -l={NAMESPACE}-username={username} -n {NAMESPACE} -o json").read()
    result = json.loads(result)
    return result
