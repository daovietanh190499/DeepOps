import os
import json
import subprocess

DEFAULT_SPAWNER = os.environ.get('SPAWNER', 'k8s')
NAMESPACE = os.environ.get('NAMESPACE', 'dohub')

def create_codehub(config):
    backslash = os.linesep
    subprocess.run([
            'helm upgrade --install --create-namespace -n {}'.format(NAMESPACE), \
            '--set "image.repository={}"'.format(config['image']), \
            '--set "image.pullPolicy=Always"', \
            '--set "image.tag=latest"', \
            '--set "podLabels.{}-username={}"'.format(NAMESPACE, config['username']), \
            '--set "secret.name={}-secret"'.format(config['username']), \
            '--set "env.secret.PASSWORD={}"'.format(config['password']), \
            '--set "serviceAccount.enable=false"', \
            '--set "serviceAccount.automount=false"', \
            '--set "serviceAccount.name=default"', \
            '--set "podSecurityContext.fsGroup=100"', \
            '--set "securityContext.capabilities.add[0]=SYS_ADMIN"', \
            '--set "securityContext.allowPrivilegeEscalation=true"', \
            '--set "securityContext.runAsUser=0"', \
            '--set "service.type=ClusterIP"', \
            '--set "service.port={}"'.format(config['defaultPort']), \
            '--set "ingress.enabled=true"', \
            '--set "ingress.className=nginx"', \
            '--set "ingress.hosts[0].host={}.vkist-hub.com"'.format(config['username']), \
            '--set "ingress.hosts[0].paths[0].path=/"', \
            '--set "ingress.hosts[0].paths[0].pathType=Prefix"', \
            '--set "ingress.tls[0].secretName=tls-{}-secret"'.format(NAMESPACE), \
            '--set "ingress.tls[0].hosts[0]={}.vkist-hub.com"'.format(config['username']), \
            '--set "mainVolume.claimName=claim-{}-{}"'.format(NAMESPACE, config['username']), \
            '--set "mainVolume.dataPath='{}'"'.format(config['path'] + '/dohub-' + config['username']), \
            '--set "volumes[0].name=shm-volume"', \
            '--set "volumes[0].emptyDir.medium=Memory"', \
            '--set "volumes[1].name=volume-{}"'.format(config['username']), \
            '--set "volumes[1].persistentVolumeClaim.claimName=claim-{}-{}"'.format(NAMESPACE, config['username']), \
            '--set "volumeMounts[0].mountPath=/dev/shm"', \
            '--set "volumeMounts[0].name=shm-volume"', \
            '--set "volumeMounts[1].mountPath=/home/coder"', \
            '--set "volumeMounts[1].name=volume-{}"'.format(config['username']), \
            '--set "resources.limits.cpu={}"'.format(config['max_cpu']), \
            '--set "resources.limits.memory={}"'.format(config['max_ram']), \
            '--set "resources.limits.{}={}"'.format(config['gpu_type'].replace('.', '\.'), config['gpu_quantity']), \
            '--set "resources.requests.cpu={}"'.format(config['cpu']), \
            '--set "resources.requests.memory={}"'.format(config['ram']), \
            '--set "resources.requests.{}={}"'.format(config['gpu_type'].replace('.', '\.'), config['gpu_quantity']), \
            '{}-{} spawners/k8s/codehub'.format(NAMESPACE, config['username']) \
        ], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

def remove_codehub(config):
    os.system(f"""helm uninstall -n {NAMESPACE} {NAMESPACE}-{config['username']} spawners/k8s/codehub""")

def get_codehub(username):
    result = os.popen(f"kubectl get pod -l={NAMESPACE}-username={username} -n {NAMESPACE} -o json").read()
    result = json.loads(result)
    return result
