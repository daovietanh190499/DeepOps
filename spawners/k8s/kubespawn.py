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
        f""" helm uninstall -n {NAMESPACE} {NAMESPACE}-{config['username']} spawners/k8s/codehub
        """
    )

def get_codehub(username):
    result = os.popen(f"kubectl get pod -l={NAMESPACE}-username={username} -n {NAMESPACE} -o json").read()
    result = json.loads(result)
    return result

# def get_servers():
#     v1 = client.CoreV1Api()
#     ret = v1.list_namespaced_pod('dohub')
#     items = []
#     for i in ret.items:
#         items.append[{
#             'name': i.metadata.name,
#             'ip': i.status.pod_ip, 
#             'state': i.status.container_statuses[0].state
#         }]
#     return items

# def get_server(username):
#     v1 = client.CoreV1Api()
#     try:
#         api_response = v1.read_namespaced_pod('dohub-' + username, 'dohub')
#     except:
#         return {
#             'state': {
#                 'message': 'Idle',
#                 'reason': 'Idling'
#             }
#         }
#     if not api_response or not  api_response.status or not api_response.status.container_statuses:
#         return {
#             'state': {
#                 'message': 'Idle',
#                 'reason': 'Idling'
#             }
#         }
#     message = 'Idle'
#     reason = 'Idling'
#     if api_response.status.container_statuses[0].state.running:
#         message = 'Running'
#         reason = 'Success'
#     elif api_response.status.container_statuses[0].state.terminated:
#         message = api_response.status.container_statuses[0].state.terminated.message
#         reason = api_response.status.container_statuses[0].state.terminated.reason
#     elif api_response.status.container_statuses[0].state.waiting:
#         message = api_response.status.container_statuses[0].state.waiting.message
#         reason = api_response.status.container_statuses[0].state.waiting.reason
#     return {
#         'name': api_response.metadata.name,
#         'ip': api_response.status.pod_ip, 
#         'state': {
#             'message': message,
#             'reason': reason
#         }
#     }

# def create_service(config):
#     k8s_client = client.ApiClient()
#     service_manifest = {
#         'apiVersion': 'v1',
#         'kind': 'Service',
#         'metadata': {
#             'name': 'dohub-' + config['username'] + '-service',
#             'namespace': 'dohub'
#         },
#         'spec': {
#             'selector': {
#                 'app': 'dohub',
#                 'heritage': 'dohub',
#                 'do.hub/username': config['username'],
#                 'release': 'dohub'
#             },
#             'ports': [{
#                 'protocol': 'TCP',
#                 'port': config['defaultPort'],
#                 'targetPort': config['defaultPort'],
#                 'name': 'user-dohub'
#             }]
#         }
#     }

#     api_response = utils.create_from_dict(k8s_client, service_manifest)
#     return api_response

# def create_pv(config):
#     k8s_client = client.ApiClient()
#     persistent_volume_manifest = {
#         'apiVersion': 'v1',
#         'kind': 'PersistentVolume',
#         'metadata': {
#             'name': 'dohub-' + config['username'],
#             'namespace': 'dohub'
#         },
#         'spec': {
#             'storageClassName': 'volume-' + config['username'],
#             'capacity': {
#                 'storage': '20Gi'
#             },
#             'accessModes': ['ReadWriteOnce'],
#             'nfs': {
#                 'path': config['path'] + '/dohub-' + config['username'],
#                 'server': config['file_server']
#             }
#         }
#     }

#     api_response = utils.create_from_dict(k8s_client, persistent_volume_manifest)
#     return api_response

# def create_pvc(config):
#     k8s_client = client.ApiClient()
#     persistent_volume_claim_manifest = {
#         'apiVersion': 'v1',
#         'kind': 'PersistentVolumeClaim',
#         'metadata': {
#             'name': 'claim-dohub-' + config['username'],
#             'namespace': 'dohub'
#         },
#         'spec': {
#             'storageClassName': 'volume-' + config['username'],
#             'accessModes': ['ReadWriteOnce'],
#             'resources': {
#                 'requests': {
#                     'storage': '10Gi'
#                 }
#             }
#         }
#     }
    
#     api_response = utils.create_from_dict(k8s_client, persistent_volume_claim_manifest)
#     return api_response

# def create_server(config):
#     k8s_client = client.ApiClient()
#     server_manifest = {
#         'apiVersion': 'v1', 
#         'kind': 'Pod', 
#         'metadata': {
#             'annotation': {
#                 'do.hub/username': config['username'],
#             },
#             'labels': {
#                 'app': 'dohub',
#                 'heritage': 'dohub',
#                 'do.hub/username': config['username'],
#                 'release': 'dohub'
#             },
#             'name': 'dohub-' + config['username'],
#             'namespace': 'dohub'
#         }, 
#         'spec': {
#             'automountServiceAccountToken': False, 
#             'containers': [
#                 {
#                     'env': [
#                         {
#                             'name': 'PASSWORD',
#                             'value': config['password'],
#                         }
#                     ],
#                     'image': config['image'], 
#                     'imagePullPolicy': 'IfNotPresent',
#                     'name': 'codeserver',
#                     'ports': [
#                         {
#                             'containerPort': config['defaultPort'],
#                             'name': 'dohub-port',
#                             'protocol': 'TCP',
#                         }
#                     ],
#                     'resources': {
#                         'limits': {
#                             'cpu': config['max_cpu'],
#                             'memory': config['max_ram'],
#                             config['gpu_type']: config['gpu_quantity'],
#                         },
#                         'requests': {
#                             'cpu': config['cpu'],
#                             'memory': config['ram'],
#                             config['gpu_type']: config['gpu_quantity'],
#                         }
#                     },
#                     'securityContext': {
#                         'capabilities': {
#                             'add': ['SYS_ADMIN']
#                         },
#                         'allowPrivilegeEscalation': True,
#                     },
#                     'terminationMessagePath': '/dev/termination-log',
#                     'terminationMessagePolicy': 'File',
#                     'volumeMounts': [
#                         {
#                             'mountPath': '/home/coder',
#                             'name': 'volume-' + config['username']
#                         },
#                         {
#                             'mountPath': '/dev/shm',
#                             'name': 'shm-volume'
#                         }
#                     ]
#                 }
#             ],
#             'dnsPolicy': 'ClusterFirst',
#             'enableServiceLinks': True,
#             'preemptionPolicy': 'PreemptLowerPriority',
#             'priority': 0,
#             'restartPolicy': 'OnFailure',
#             'securityContext': {
#                 'fsGroup': 100
#             },
#             'serviceAccount': 'default',
#             'serviceAccountName': 'default',
#             'terminationGracePeriodSeconds': 30,
#             'volumes': [
#                 {
#                     'name': 'volume-' + config['username'],
#                     'persistentVolumeClaim': {
#                         'claimName': 'claim-dohub-' + config['username']
#                     }
#                 },
#                 {
#                     'emptyDir': {
#                         'medium': 'Memory'
#                     },
#                     'name': 'shm-volume'
#                 }
#             ]
#         }
#     }

#     if config['not_use_gpu']:
#         del server_manifest['spec']['containers'][0]['resources']['limits'][config['gpu_type']]
#         del server_manifest['spec']['containers'][0]['resources']['requests'][config['gpu_type']]
#         del server_manifest['spec']['containers'][0]['securityContext']

#     api_response = utils.create_from_dict(k8s_client, server_manifest)
#     return api_response