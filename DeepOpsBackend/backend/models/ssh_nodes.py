import uuid

from django.db import models


class SSHNodeManagerKey(models.Model):
    """Singleton SSH key pair used by the hub to reach admin-managed SSH nodes."""

    id = models.PositiveSmallIntegerField(primary_key=True, default=1)
    public_key = models.TextField()
    encrypted_private_key = models.TextField()
    fingerprint = models.CharField(max_length=128, blank=True, default='')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'SSH node manager key'

    def to_dict(self) -> dict:
        return {
            'public_key': self.public_key,
            'fingerprint': self.fingerprint,
            'updated_at': self.updated_at.isoformat() if self.updated_at else '',
        }


class SSHNode(models.Model):
    """External SSH host managed from the admin cluster page."""

    STATUS_UNKNOWN = 'unknown'
    STATUS_CHECKING = 'checking'
    STATUS_ONLINE = 'online'
    STATUS_OFFLINE = 'offline'
    STATUS_CHOICES = (
        (STATUS_UNKNOWN, 'Unknown'),
        (STATUS_CHECKING, 'Checking'),
        (STATUS_ONLINE, 'Online'),
        (STATUS_OFFLINE, 'Offline'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    label = models.CharField(max_length=255, blank=True, default='')
    host = models.CharField(max_length=255)
    port = models.PositiveIntegerField(default=22)
    username = models.CharField(max_length=128)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_UNKNOWN)
    health_line = models.TextField(blank=True, default='')
    last_error = models.TextField(blank=True, default='')
    last_checked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def display_name(self) -> str:
        return (self.label or '').strip() or self.host

    def to_dict(self) -> dict:
        return {
            'id': str(self.id),
            'label': self.label,
            'display_name': self.display_name(),
            'host': self.host,
            'port': self.port,
            'username': self.username,
            'status': self.status,
            'health_line': self.health_line,
            'last_error': self.last_error,
            'last_checked_at': self.last_checked_at.isoformat() if self.last_checked_at else '',
            'created_at': self.created_at.isoformat() if self.created_at else '',
            'updated_at': self.updated_at.isoformat() if self.updated_at else '',
        }
