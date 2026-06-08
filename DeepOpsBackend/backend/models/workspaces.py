import re
import uuid

from django.db import models
from django.utils.text import slugify

from .drives import UserDrive
from .users import User


def _default_env():
    return {}


def _default_ports():
    return []


def _default_command():
    return []


class DockerImage(models.Model):
    label = models.CharField(max_length=255)
    repository = models.CharField(max_length=512)
    default_tag = models.CharField(max_length=128, default='latest')
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'label']

    def __str__(self):
        return f'{self.label} ({self.repository}:{self.default_tag})'


class WorkspaceDriveMount(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        'Workspace',
        on_delete=models.CASCADE,
        related_name='extra_drive_mounts',
    )
    user_drive = models.ForeignKey(UserDrive, on_delete=models.PROTECT, related_name='extra_workspace_mounts')
    mount_path = models.CharField(max_length=256)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order', 'created_at']
        unique_together = (
            ('workspace', 'user_drive'),
            ('workspace', 'mount_path'),
        )

    def __str__(self):
        return f'{self.workspace.slug}:{self.mount_path}'


class Workspace(models.Model):
    STATE_OFFLINE = 'offline'
    STATE_RUNNING = 'running'
    STATE_PENDING_START = 'pending_start'
    STATE_PENDING_STOP = 'pending_stop'
    STATE_CHOICES = (
        (STATE_OFFLINE, 'offline'),
        (STATE_RUNNING, 'running'),
        (STATE_PENDING_START, 'pending_start'),
        (STATE_PENDING_STOP, 'pending_stop'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='workspaces')
    name = models.CharField(max_length=128)
    slug = models.SlugField(max_length=48)
    cpu = models.PositiveIntegerField(default=2)
    ram = models.CharField(max_length=64, default='4G')
    user_drive = models.ForeignKey(
        UserDrive,
        on_delete=models.PROTECT,
        related_name='workspaces',
        null=True,
        blank=True,
    )
    mount_path = models.CharField(max_length=256, default='/home/coder')
    gpu = models.CharField(max_length=255, blank=True, default='')
    docker_repository = models.CharField(max_length=512, default='codercom/code-server')
    docker_tag = models.CharField(max_length=128, default='4.89.0-ubuntu')
    env_vars = models.JSONField(default=_default_env, blank=True)
    exposed_ports = models.JSONField(default=_default_ports, blank=True)
    container_command = models.JSONField(default=_default_command, blank=True)
    state = models.CharField(max_length=32, choices=STATE_CHOICES, default=STATE_OFFLINE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        unique_together = ('user', 'slug')

    def __str__(self):
        return f'{self.user.username}/{self.slug}'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._make_unique_slug(self.name)
        super().save(*args, **kwargs)

    def _make_unique_slug(self, base: str) -> str:
        raw = slugify(base) or 'workspace'
        raw = re.sub(r'[^a-z0-9-]', '', raw.lower())[:40] or 'workspace'
        candidate = raw
        n = 0
        while Workspace.objects.filter(user_id=self.user_id, slug=candidate).exclude(pk=self.pk).exists():
            n += 1
            candidate = f'{raw}-{n}'[:48]
        return candidate

    @property
    def release_name(self) -> str:
        ns = __import__('os').environ.get('NAMESPACE', 'dohub')
        return f'{ns}-{self.user.username}-{self.slug}'

    @property
    def hostname(self) -> str:
        domain = __import__('os').environ.get('DOMAIN_NAME', 'dohub.com')
        return f'{self.slug}-{self.user.username}.{domain}'

    def to_config_dict(self) -> dict:
        return {
            'id': str(self.id),
            'name': self.name,
            'slug': self.slug,
            'username': self.user.username,
            'cpu': self.cpu,
            'ram': self.ram,
            'drive_id': str(self.user_drive_id) if self.user_drive_id else None,
            'drive_name': self.user_drive.name if self.user_drive_id else None,
            'drive_size': self.user_drive.size if self.user_drive_id else None,
            'mount_path': self.mount_path,
            'gpu': self.gpu or 'none',
            'docker_repository': self.docker_repository,
            'docker_tag': self.docker_tag,
            'env_vars': self.env_vars or {},
            'exposed_ports': self.exposed_ports or [],
            'container_command': self.container_command or [],
            'state': self.state,
            'hostname': self.hostname,
            'release_name': self.release_name,
        }
