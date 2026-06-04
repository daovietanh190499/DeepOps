import os
import re
import uuid

from django.db import models
from django.utils.text import slugify

from .users import User


class UserDrive(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_BOUND = 'bound'
    STATUS_LOST = 'lost'
    STATUS_CHOICES = (
        (STATUS_PENDING, 'pending'),
        (STATUS_BOUND, 'bound'),
        (STATUS_LOST, 'lost'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='drives')
    name = models.CharField(max_length=128)
    slug = models.SlugField(max_length=48)
    size = models.CharField(max_length=32, default='20Gi')
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('user', 'slug')

    def __str__(self):
        return f'{self.user.username}/{self.slug}'

    @property
    def claim_name(self) -> str:
        ns = os.environ.get('NAMESPACE', 'dohub')
        return f'drive-{ns}-{self.user.username}-{self.slug}'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._make_unique_slug(self.name)
        super().save(*args, **kwargs)

    def _make_unique_slug(self, base: str) -> str:
        raw = slugify(base) or 'drive'
        raw = re.sub(r'[^a-z0-9-]', '', raw.lower())[:40] or 'drive'
        candidate = raw
        n = 0
        while UserDrive.objects.filter(user_id=self.user_id, slug=candidate).exclude(pk=self.pk).exists():
            n += 1
            candidate = f'{raw}-{n}'[:48]
        return candidate

    def to_dict(self) -> dict:
        return {
            'id': str(self.id),
            'name': self.name,
            'slug': self.slug,
            'size': self.size,
            'status': self.status,
            'claim_name': self.claim_name,
            'owner': self.user.username,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }
