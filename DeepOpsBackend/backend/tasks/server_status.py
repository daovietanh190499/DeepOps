import os
from DeepOpsBackend.celery import app

from backend.models import User, Server
from backend.serializers import UserSerializer, ServerSerializer

NAMESPACE = os.environ.get('NAMESPACE', 'dohub')

@app.task
def check_server_status():
    # result = os.popen(f"kubectl get pod -l={NAMESPACE}-username={user.data['username']} -n {NAMESPACE} -o json").read()
    result = os.popen(f"kubectl get pod -n {NAMESPACE} -o json").read()
    result = json.loads(result)
    return result