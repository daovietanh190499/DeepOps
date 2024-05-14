import os
import json
import subprocess

DEFAULT_SPAWNER = os.environ.get('SPAWNER', 'k8s')
NAMESPACE = os.environ.get('NAMESPACE', 'dohub')

def create_codehub(config):
    gpu_type = config['gpu_type'].replace('.', '\.')
    gpu_config = f"""
            --set resources.limits.{gpu_type}={config['gpu_quantity']} \
            --set resources.requests.{gpu_type}={config['gpu_quantity']}
    """
    command = f"""helm upgrade --install --create-namespace -n {NAMESPACE} \
            --set image.repository={config['image']} \
            --set image.pullPolicy=IfNotPresent \
            --set image.tag=4.89.0-ubuntu \
            --set podLabels.{NAMESPACE}-username={config['username']} \
            --set secret.name={config['username']}-secret \
            --set env.secret.PASSWORD={config['password']} \
            --set serviceAccount.enable=false \
            --set serviceAccount.automount=false \
            --set serviceAccount.name=default \
            --set podSecurityContext.fsGroup=100 \
            --set securityContext.capabilities.add[0]=SYS_ADMIN \
            --set securityContext.allowPrivilegeEscalation=true \
            --set securityContext.runAsUser=0 \
            --set service.type=ClusterIP \
            --set service.port={config['defaultPort']} \
            --set ingress.enabled=true \
            --set "ingress.annotation.nginx\.ingress\.kubernetes\.io/proxy-body-size = 0" \
            --set "ingress.annotation.nginx\.ingress\.kubernetes\.io/proxy-read-timeout = 600" \
            --set "ingress.annotation.nginx\.ingress\.kubernetes\.io/proxy-send-timeout = 600" \
            --set ingress.className=nginx \
            --set ingress.hosts[0].host={config['username']}.vkist-hub.com \
            --set ingress.hosts[0].paths[0].path=/ \
            --set ingress.hosts[0].paths[0].pathType=Prefix \
            --set ingress.tls[0].secretName=tls-{NAMESPACE}-secret \
            --set ingress.tls[0].hosts[0]={config['username']}.vkist-hub.com \
            --set mainVolume.claimName=claim-{NAMESPACE}-{config['username']} \
            --set mainVolume.dataPath='{config['path'] + '/dohub-' + config['username']}' \
            --set volumes[0].name=shm-volume \
            --set volumes[0].emptyDir.medium=Memory \
            --set volumes[1].name=volume-{config['username']} \
            --set volumes[1].persistentVolumeClaim.claimName=claim-{NAMESPACE}-{config['username']} \
            --set volumeMounts[0].mountPath=/dev/shm \
            --set volumeMounts[0].name=shm-volume \
            --set volumeMounts[1].mountPath=/home/coder \
            --set volumeMounts[1].name=volume-{config['username']} \
            --set resources.limits.cpu={config['max_cpu']} \
            --set resources.limits.memory={config['max_ram']} \
            --set resources.requests.cpu={config['cpu']} \
            --set resources.requests.memory={config['ram']} \
            {gpu_config if not config['not_use_gpu'] else ''} \
            {NAMESPACE}-{config['username']} spawners/k8s/codehub"""
    output = subprocess.run(command.split(), capture_output = True, text=True, universal_newlines=True)
    return command, output.stdout

def remove_codehub(config):
    os.system(f"""helm uninstall -n {NAMESPACE} {NAMESPACE}-{config['username']} spawners/k8s/codehub""")

def get_codehub(username):
    result = os.popen(f"kubectl get pod -l={NAMESPACE}-username={username} -n {NAMESPACE} -o json").read()
    result = json.loads(result)
    return result
