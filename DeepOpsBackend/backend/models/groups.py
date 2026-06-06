import uuid

from django.db import models

from .users import User


class ResourceGroup(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=128, unique=True)
    max_cpu = models.PositiveIntegerField(help_text='Max vCPU per server for each member')
    max_ram_g = models.PositiveIntegerField(help_text='Max RAM (GB) per server for each member')
    max_drive_size_gi = models.PositiveIntegerField(help_text='Max drive size (Gi) per drive for each member')
    max_gpu_vram_g = models.PositiveIntegerField(
        default=0,
        help_text='Max GPU VRAM (GB) per server for each member; 0 disables GPU',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class ResourceGroupMember(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(ResourceGroup, on_delete=models.CASCADE, related_name='members')
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='resource_group_membership')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username}@{self.group.name}'
