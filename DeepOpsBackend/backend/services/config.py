import os
from functools import lru_cache

import yaml

CONFIG_PATH = os.environ.get('CONFIG_PATH', '/etc/dohub/config.yaml')
FALLBACK_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'config',
    'config.yaml',
)


@lru_cache(maxsize=1)
def get_hub_config():
    path = CONFIG_PATH if os.path.exists(CONFIG_PATH) else FALLBACK_CONFIG_PATH
    with open(path, 'r', encoding='utf-8') as stream:
        return yaml.safe_load(stream)
