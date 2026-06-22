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


def _default_ws_tunnel_ports():
    return []


class DockerImage(models.Model):
    label = models.CharField(max_length=255)
    repository = models.CharField(max_length=512)
    default_tag = models.CharField(max_length=128, default='latest')
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text='Selectable image tags; default_tag should be included',
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='docker_images',
    )
    is_accepted = models.BooleanField(
        default=True,
        help_text='User-submitted images require admin acceptance before use in servers',
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order', 'label']

    def __str__(self):
        return f'{self.label} ({self.repository}:{self.default_tag})'

    def available_tags(self) -> list[str]:
        raw = self.tags if isinstance(self.tags, list) else []
        tags = [str(t).strip() for t in raw if str(t).strip()]
        if not tags and self.default_tag:
            tags = [self.default_tag]
        elif self.default_tag and self.default_tag not in tags:
            tags.insert(0, self.default_tag)
        return tags or ['latest']

    def to_dict(self) -> dict:
        creator = self.created_by.username if self.created_by_id else ''
        creator_image = self.created_by.image if self.created_by_id else ''
        return {
            'id': self.id,
            'label': self.label,
            'repository': self.repository,
            'default_tag': self.default_tag,
            'tags': self.available_tags(),
            'creator': creator,
            'creator_image': creator_image,
            'creator_id': self.created_by_id,
            'is_accepted': self.is_accepted,
            'is_active': self.is_active,
            'sort_order': self.sort_order,
            'created_at': self.created_at.isoformat() if self.created_at else '',
        }


class WorkspaceFileMount(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        'Workspace',
        on_delete=models.CASCADE,
        related_name='file_mounts',
    )
    filename = models.CharField(max_length=255)
    configmap_key = models.CharField(max_length=253)
    content = models.TextField()
    mount_path = models.CharField(max_length=256)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order', 'created_at']
        unique_together = (
            ('workspace', 'mount_path'),
            ('workspace', 'configmap_key'),
        )

    def __str__(self):
        return f'{self.workspace.slug}:{self.mount_path}'


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
    cpu = models.FloatField(default=2)
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
    node_hostname = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='Kubernetes node hostname to pin this workspace to (empty = auto schedule)',
    )
    env_vars = models.JSONField(default=_default_env, blank=True)
    exposed_ports = models.JSONField(default=_default_ports, blank=True)
    ws_tunnel_ports = models.JSONField(
        default=_default_ws_tunnel_ports,
        blank=True,
        help_text='Main-container TCP ports exposed via wstunnel sidecar',
    )
    backup_enabled = models.BooleanField(default=False)
    backup_schedule = models.CharField(max_length=128, blank=True, default='')
    backup_remote = models.CharField(max_length=512, blank=True, default='')
    backup_folders = models.JSONField(default=list, blank=True)
    backup_rclone_config = models.TextField(blank=True, default='')
    container_command = models.JSONField(default=_default_command, blank=True)
    privileged = models.BooleanField(
        default=False,
        help_text='Run code-server container with securityContext.privileged=true',
    )
    custom_hostname = models.CharField(
        max_length=253,
        blank=True,
        null=True,
        unique=True,
        help_text='Optional ingress hostname override; empty uses default slug-user.domain',
    )
    EXEC_SHELL_BASH = 'bash'
    EXEC_SHELL_SH = 'sh'
    EXEC_SHELL_CHOICES = (
        (EXEC_SHELL_BASH, 'bash'),
        (EXEC_SHELL_SH, 'sh'),
    )
    exec_shell = models.CharField(
        max_length=16,
        choices=EXEC_SHELL_CHOICES,
        default=EXEC_SHELL_BASH,
        help_text='Shell used by SSH bridge kubectl exec (bash or sh)',
    )
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

    def delete(self, *args, **kwargs):
        from backend.services.workspace_db import purge_legacy_workspace_rows
        purge_legacy_workspace_rows(self.pk)
        super().delete(*args, **kwargs)

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
    def default_hostname(self) -> str:
        domain = __import__('os').environ.get('DOMAIN_NAME', 'dohub.com')
        return f'{self.slug}-{self.user.username}.{domain}'

    @property
    def hostname(self) -> str:
        custom = (self.custom_hostname or '').strip().lower().rstrip('.')
        if custom:
            return custom
        return self.default_hostname

    def to_config_dict(self) -> dict:
        return {
            'id': str(self.id),
            'name': self.name,
            'slug': self.slug,
            'username': self.user.username,
            'cpu': self.cpu,
            'ram': self.ram,
            'node_hostname': self.node_hostname or '',
            'drive_id': str(self.user_drive_id) if self.user_drive_id else None,
            'drive_name': self.user_drive.name if self.user_drive_id and self.user_drive else None,
            'drive_size': self.user_drive.size if self.user_drive_id and self.user_drive else None,
            'mount_path': self.mount_path,
            'gpu': self.gpu or 'none',
            'docker_repository': self.docker_repository,
            'docker_tag': self.docker_tag,
            'env_vars': self.env_vars or {},
            'exposed_ports': self.exposed_ports or [],
            'ws_tunnel_ports': self.ws_tunnel_ports if isinstance(self.ws_tunnel_ports, list) else [],
            'container_command': self.container_command or [],
            'privileged': self.privileged,
            'custom_hostname': (self.custom_hostname or '').strip(),
            'default_hostname': self.default_hostname,
            'exec_shell': self.exec_shell or self.EXEC_SHELL_BASH,
            'state': self.state,
            'hostname': self.hostname,
            'release_name': self.release_name,
        }
