import os
from celery import shared_task

from backend.models import User, Server
from backend.serializers import UserSerializer, ServerSerializer

DEFAULT_SPAWNER = os.environ.get('SPAWNER', 'k8s')
NAMESPACE = os.environ.get('NAMESPACE', 'dohub')
DOMAIN_NAME = os.environ.get('DOMAIN_NAME', 'dohub.com')
DEFAULT_PORT = os.environ.get('DEFAULT_PORT', 8080)
DEFAULT_PATH = os.environ.get('DEFAULT_PATH', '/mnt/nas0')

@shared_task
def create_server_task(user):
    if user['state'] == 'terminated':
        gpu_config = ""
        if user['inferencing_server']['gpu'] != 'none':
            gpu_type = user['inferencing_server']['gpu'].split(":")[0].replace('.', '\.')
            gpu_quantity = user['inferencing_server']['gpu'].split(":")[1]
            gpu_config = f"""
                    --set resources.limits.{gpu_type}={gpu_quantity} \
                    --set resources.requests.{gpu_type}={gpu_quantity}
            """
        command = f"""helm upgrade --install --create-namespace -n {NAMESPACE} \
                --set image.repository={user['inferencing_server']['docker_image']} \
                --set image.pullPolicy=IfNotPresent \
                --set image.tag={user['inferencing_server']['docker_tag']} \
                --set podLabels.{NAMESPACE}-username={user['username']} \
                --set secret.name={user['username']}-secret \
                --set env.secret.PASSWORD={user['password']} \
                --set serviceAccount.enable=false \
                --set serviceAccount.automount=false \
                --set serviceAccount.name=default \
                --set podSecurityContext.fsGroup=100 \
                --set securityContext.capabilities.add[0]=SYS_ADMIN \
                --set securityContext.allowPrivilegeEscalation=true \
                --set securityContext.runAsUser=0 \
                --set service.type=ClusterIP \
                --set service.port={DEFAULT_PORT} \
                --set ingress.enabled=true \
                --set ingress.annotations.nginx\.ingress\.kubernetes\.io/proxy-body-size='0' \
                --set ingress.annotations.nginx\.ingress\.kubernetes\.io/proxy-read-timeout='600' \
                --set ingress.annotations.nginx\.ingress\.kubernetes\.io/proxy-send-timeout='600' \
                --set ingress.className=nginx \
                --set ingress.hosts[0].host={user['username']}.{DOMAIN_NAME} \
                --set ingress.hosts[0].paths[0].path=/ \
                --set ingress.hosts[0].paths[0].pathType=Prefix \
                --set ingress.tls[0].secretName=tls-{NAMESPACE}-secret \
                --set ingress.tls[0].hosts[0]={user['username']}.{DOMAIN_NAME} \
                --set mainVolume.claimName=claim-{NAMESPACE}-{user['username']} \
                --set mainVolume.dataPath='{DEFAULT_PATH + '/dohub-' + user['username']}' \
                --set volumes[0].name=shm-volume \
                --set volumes[0].emptyDir.medium=Memory \
                --set volumes[1].name=volume-{user['username']} \
                --set volumes[1].persistentVolumeClaim.claimName=claim-{NAMESPACE}-{user['username']} \
                --set volumeMounts[0].mountPath=/dev/shm \
                --set volumeMounts[0].name=shm-volume \
                --set volumeMounts[1].mountPath=/home/coder \
                --set volumeMounts[1].name=volume-{user['username']} \
                --set resources.limits.cpu={user['inferencing_server']['cpu']} \
                --set resources.limits.memory={user['inferencing_server']['ram']} \
                --set resources.requests.cpu={user['inferencing_server']['cpu']} \
                --set resources.requests.memory={user['inferencing_server']['ram']} \
                {gpu_config} \
                {NAMESPACE}-{user['username']} spawners/k8s/codehub"""
        output = subprocess.run(command.split(), capture_output = True, text=True, universal_newlines=True)

@shared_task
def terminate_server_task(user):
    os.system(f"""helm uninstall -n {NAMESPACE} {NAMESPACE}-{user['username']} spawners/k8s/codehub""")