import uuid

from django.db import models

from .servers import ServerOption


class User(models.Model):
    ROLE_ADMIN = 'admin'
    ROLE_NORMAL = 'normal_user'
    ROLE_CHOICES = (
        (ROLE_ADMIN, 'admin'),
        (ROLE_NORMAL, 'normal_user'),
    )

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

    github_access_token = models.CharField(max_length=255, blank=True, default='')
    github_id = models.BigIntegerField(null=True, blank=True)
    username = models.CharField(max_length=255, unique=True)
    image = models.TextField(blank=True, default='')
    access_key = models.CharField(max_length=255, blank=True, default='')
    server_ip = models.CharField(max_length=64, blank=True, default='')
    role = models.CharField(max_length=32, choices=ROLE_CHOICES, default=ROLE_NORMAL)
    is_accept = models.BooleanField(default=False)
    current_server = models.ForeignKey(
        ServerOption,
        on_delete=models.SET_NULL,
        null=True,
        related_name='current_users',
    )
    state = models.CharField(max_length=32, choices=STATE_CHOICES, default=STATE_OFFLINE)
    access_password = models.CharField(max_length=255, blank=True, default='')
    last_activity = models.FloatField(null=True, blank=True)

    allowed_servers = models.ManyToManyField(
        ServerOption,
        through='UserServer',
        related_name='users',
    )

    class Meta:
        ordering = ['username']

    def __str__(self):
        return self.username

    def issue_access_key(self):
        self.access_key = str(uuid.uuid4())
        self.save(update_fields=['access_key'])
        return self.access_key

    def ensure_access_password(self):
        if not self.access_password:
            self.access_password = f'{self.username}-{uuid.uuid4().hex[:8]}'
            self.save(update_fields=['access_password'])


class UserServer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_servers')
    server = models.ForeignKey(ServerOption, on_delete=models.CASCADE, related_name='user_servers')

    class Meta:
        unique_together = ('user', 'server')
