from backend.models import DockerImage
from backend.services.config import get_hub_config


def seed_docker_images():
    from django.db import connection

    if 'backend_dockerimage' not in connection.introspection.table_names():
        return

    try:
        config = get_hub_config()
    except (FileNotFoundError, OSError):
        return

    images = config.get('initDockerImages')
    if not images:
        images = [
            {
                'label': 'Code Server',
                'repository': 'codercom/code-server',
                'default_tag': '4.89.0-ubuntu',
                'sort_order': 0,
            },
        ]

    for i, item in enumerate(images):
        tags = item.get('tags')
        if not isinstance(tags, list) or not tags:
            tags = [item.get('default_tag', 'latest')]
        DockerImage.objects.get_or_create(
            repository=item['repository'],
            defaults={
                'label': item.get('label', item['repository']),
                'default_tag': item.get('default_tag', tags[0]),
                'tags': tags,
                'is_active': item.get('is_active', True),
                'sort_order': item.get('sort_order', i),
            },
        )


def seed_server_options():
    """Legacy — no longer seeds plan templates."""
    pass
