from django.apps import AppConfig


class BackendConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend'

    def ready(self):
        from django.db.models.signals import post_migrate

        def _seed(sender, **kwargs):
            from backend.services.seed import seed_docker_images
            seed_docker_images()

        post_migrate.connect(_seed, sender=self)
