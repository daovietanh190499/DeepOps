from kubernetes import client, config, utils

# config.load_incluster_config()

def get_servers():
    v1 = client.CoreV1Api()
    try:
        ret = v1.list_namespaced_pod('dohub')
    except:
        return None
    items = []
    for i in ret.items:
        items.append[{
            'name': i.metadata.name,
            'ip': i.status.pod_ip, 
            'state': i.status.container_statuses[0].state
        }]
    return items

def get_pvc(username):
    v1 = client.CoreV1Api()
    try:
        api_response = v1.read_namespaced_persistent_volume_claim('claim-dohub-' + username, 'dohub')
    except:
        return None
    return api_response

def get_pv(username):
    v1 = client.CoreV1Api()
    try:
        api_response = v1.read_namespaced_persistent_volume('dohub-' + username, 'dohub')
    except:
        return None
    return api_response

def get_server(username):
    v1 = client.CoreV1Api()
    try:
        api_response = v1.read_namespaced_pod('dohub-' + username, 'dohub')
    except:
        return None
    if not api_response:
        return None
    return {
        'name': api_response.metadata.name,
        'ip': api_response.status.pod_ip, 
        'state': api_response.status.container_statuses[0].state 
    }

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
    try:
        api_response = utils.create_from_dict(k8s_client, persistent_volume_manifest)
    except:
        return None
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

    try:
        api_response = utils.create_from_dict(k8s_client, persistent_volume_claim_manifest)
    except:
        return None
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
            'automountServiceAccountToken': 'false', 
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
                    'lifecycle': {},
                    'name': 'codeserver',
                    'ports': [
                        {
                            'containerPort': 8443,
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

    try:
        api_response = utils.create_from_dict(k8s_client, server_manifest)
    except:
        return None
    return api_response

def delete_server(username):
    v1 = client.CoreV1Api()
    try:
        api_response = v1.delete_namespaced_pod('dohub-' + username, 'dohub')
    except:
        return None
    return api_response

def delete_pvc(username):
    v1 = client.CoreV1Api()
    try:
        api_response = v1.delete_namespaced_persistent_volume_claim('claim-dohub-' + username, 'dohub')
    except:
        return None
    return api_response

def delete_pv(username):
    v1 = client.CoreV1Api()
    try:
        api_response = v1.delete_namespaced_persistent_volume('dohub-' + username, 'dohub')
    except:
        return None
    return api_response