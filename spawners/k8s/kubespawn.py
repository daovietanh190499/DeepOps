import yaml
from kubernetes import client, config, utils

with open("/etc/dohub/config.yaml", 'r') as stream:
    config_file = yaml.safe_load(stream)

if config_file['spawner'] == 'local':
    config.load_config()
else:
    config.load_incluster_config()

def get_servers():
    v1 = client.CoreV1Api()
    ret = v1.list_namespaced_pod('dohub')
    items = []
    for i in ret.items:
        items.append[{
            'name': i.metadata.name,
            'ip': i.status.pod_ip, 
            'state': i.status.container_statuses[0].state
        }]
    return items

def get_service(username):
    v1 = client.CoreV1Api()
    api_response = v1.read_namespaced_service('dohub-' + username + '-service', 'dohub')
    return api_response

def get_pvc(username):
    v1 = client.CoreV1Api()
    api_response = v1.read_namespaced_persistent_volume_claim('claim-dohub-' + username, 'dohub')
    return api_response

def get_pv(username):
    v1 = client.CoreV1Api()
    api_response = v1.read_persistent_volume('dohub-' + username)
    return api_response

def get_server(username):
    v1 = client.CoreV1Api()
    try:
        api_response = v1.read_namespaced_pod('dohub-' + username, 'dohub')
    except:
        return {
            'state': {
                'message': 'Idle',
                'reason': 'Idling'
            }
        }
    if not api_response or not  api_response.status or not api_response.status.container_statuses:
        return {
            'state': {
                'message': 'Idle',
                'reason': 'Idling'
            }
        }
    message = 'Idle'
    reason = 'Idling'
    if api_response.status.container_statuses[0].state.running:
        message = 'Running'
        reason = 'Success'
    elif api_response.status.container_statuses[0].state.terminated:
        message = api_response.status.container_statuses[0].state.terminated.message
        reason = api_response.status.container_statuses[0].state.terminated.reason
    elif api_response.status.container_statuses[0].state.waiting:
        message = api_response.status.container_statuses[0].state.waiting.message
        reason = api_response.status.container_statuses[0].state.waiting.reason
    return {
        'name': api_response.metadata.name,
        'ip': api_response.status.pod_ip, 
        'state': {
            'message': message,
            'reason': reason
        }
    }

def create_service(config):
    k8s_client = client.ApiClient()
    service_manifest = {
        'apiVersion': 'v1',
        'kind': 'Service',
        'metadata': {
            'name': 'dohub-' + config['username'] + '-service',
            'namespace': 'dohub'
        },
        'spec': {
            'selector': {
                'app': 'dohub',
                'heritage': 'dohub',
                'do.hub/username': config['username'],
                'release': 'dohub'
            },
            'ports': [{
                'protocol': 'TCP',
                'port': config['defaultPort'],
                'targetPort': config['defaultPort'],
                'name': 'user-dohub'
            }]
        }
    }

    api_response = utils.create_from_dict(k8s_client, service_manifest)
    return api_response

def create_pv(config):
    k8s_client = client.ApiClient()
    persistent_volume_manifest = {
        'apiVersion': 'v1',
        'kind': 'PersistentVolume',
        'metadata': {
            'name': 'dohub-' + config['username'],
            'namespace': 'dohub'
        },
        'spec': {
            'storageClassName': 'volume-' + config['username'],
            'capacity': {
                'storage': '20Gi'
            },
            'accessModes': ['ReadWriteOnce'],
            'nfs': {
                'path': config['path'] + '/dohub-' + config['username'],
                'server': config['file_server']
            }
        }
    }

    api_response = utils.create_from_dict(k8s_client, persistent_volume_manifest)
    return api_response

def create_pvc(config):
    k8s_client = client.ApiClient()
    persistent_volume_claim_manifest = {
        'apiVersion': 'v1',
        'kind': 'PersistentVolumeClaim',
        'metadata': {
            'name': 'claim-dohub-' + config['username'],
            'namespace': 'dohub'
        },
        'spec': {
            'storageClassName': 'volume-' + config['username'],
            'accessModes': ['ReadWriteOnce'],
            'resources': {
                'requests': {
                    'storage': '10Gi'
                }
            }
        }
    }
    
    api_response = utils.create_from_dict(k8s_client, persistent_volume_claim_manifest)
    return api_response

def create_server(config):
    k8s_client = client.ApiClient()
    server_manifest = {
        'apiVersion': 'v1', 
        'kind': 'Pod', 
        'metadata': {
            'annotation': {
                'do.hub/username': config['username'],
            },
            'labels': {
                'app': 'dohub',
                'heritage': 'dohub',
                'do.hub/username': config['username'],
                'release': 'dohub'
            },
            'name': 'dohub-' + config['username'],
            'namespace': 'dohub'
        }, 
        'spec': {
            'automountServiceAccountToken': False, 
            'containers': [
                {
                    'env': [
                        {
                            'name': 'PASSWORD',
                            'value': config['password'],
                        }
                    ],
                    'image': config['image'], 
                    'imagePullPolicy': 'IfNotPresent',
                    'name': 'codeserver',
                    'ports': [
                        {
                            'containerPort': config['defaultPort'],
                            'name': 'dohub-port',
                            'protocol': 'TCP',
                        }
                    ],
                    'resources': {
                        'limits': {
                            'cpu': config['max_cpu'],
                            'memory': config['max_ram'],
                            config['gpu_type']: config['gpu_quantity'],
                        },
                        'requests': {
                            'cpu': config['cpu'],
                            'memory': config['ram'],
                            config['gpu_type']: config['gpu_quantity'],
                        }
                    },
                    'securityContext': {
                        'capabilities': {
                            'add': ['SYS_ADMIN']
                        },
                        'allowPrivilegeEscalation': True,
                    },
                    'terminationMessagePath': '/dev/termination-log',
                    'terminationMessagePolicy': 'File',
                    'volumeMounts': [
                        {
                            'mountPath': '/home/coder',
                            'name': 'volume-' + config['username']
                        },
                        {
                            'mountPath': '/dev/shm',
                            'name': 'shm-volume'
                        }
                    ]
                }
            ],
            'dnsPolicy': 'ClusterFirst',
            'enableServiceLinks': True,
            'preemptionPolicy': 'PreemptLowerPriority',
            'priority': 0,
            'restartPolicy': 'OnFailure',
            'securityContext': {
                'fsGroup': 100
            },
            'serviceAccount': 'default',
            'serviceAccountName': 'default',
            'terminationGracePeriodSeconds': 30,
            'volumes': [
                {
                    'name': 'volume-' + config['username'],
                    'persistentVolumeClaim': {
                        'claimName': 'claim-dohub-' + config['username']
                    }
                },
                {
                    'emptyDir': {
                        'medium': 'Memory'
                    },
                    'name': 'shm-volume'
                }
            ]
        }
    }

    if config['not_use_gpu']:
        del server_manifest['spec']['containers'][0]['resources']['limits'][config['gpu_type']]
        del server_manifest['spec']['containers'][0]['resources']['requests'][config['gpu_type']]
        del server_manifest['spec']['containers'][0]['securityContext']

    api_response = utils.create_from_dict(k8s_client, server_manifest)
    return api_response

def delete_server(username):
    v1 = client.CoreV1Api()
    api_response = v1.delete_namespaced_pod('dohub-' + username, 'dohub')
    return api_response

def delete_pvc(username):
    v1 = client.CoreV1Api()
    api_response = v1.delete_namespaced_persistent_volume_claim('claim-dohub-' + username, 'dohub')
    return api_response

def delete_pv(username):
    v1 = client.CoreV1Api()
    api_response = v1.delete_persistent_volume('dohub-' + username)
    return api_response