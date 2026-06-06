import uuid

from django.db import models

from .workspaces import Workspace


class WorkspaceSSHKey(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.OneToOneField(
        Workspace,
        on_delete=models.CASCADE,
        related_name='ssh_key',
    )
    public_key = models.TextField()
    private_key_encrypted = models.TextField()
    host_key_encrypted = models.TextField(blank=True, default='')
    fingerprint = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'ssh:{self.workspace_id}'
