import os

NAMESPACE = os.environ.get('NAMESPACE', 'dohub')
DOMAIN_NAME = os.environ.get('DOMAIN_NAME', 'dohub.com')
DEFAULT_PORT = os.environ.get('DEFAULT_PORT', '8080')
CODEHUB_CHART_PATH = os.environ.get(
    'CODEHUB_CHART_PATH',
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', '..', '..', 'charts', 'codehub')
    ),
)
