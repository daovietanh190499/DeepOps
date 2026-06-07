from django.db import models


class PlatformEquipmentOption(models.Model):
    CATEGORY_CPU = 'cpu'
    CATEGORY_RAM = 'ram'
    CATEGORY_GPU = 'gpu'
    CATEGORY_DRIVE_SIZE = 'drive_size'
    CATEGORY_CHOICES = (
        (CATEGORY_CPU, 'cpu'),
        (CATEGORY_RAM, 'ram'),
        (CATEGORY_GPU, 'gpu'),
        (CATEGORY_DRIVE_SIZE, 'drive_size'),
    )

    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES)
    value = models.CharField(max_length=64)
    vram_g = models.PositiveIntegerField(default=0, help_text='GPU VRAM in GB (gpu category only)')
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['category', 'sort_order', 'value']
        unique_together = ('category', 'value')

    def __str__(self):
        return f'{self.category}:{self.value}'


class ServerPlanTemplate(models.Model):
    name = models.CharField(max_length=128, unique=True)
    image = models.CharField(max_length=255, default='logo.png')
    cpu = models.PositiveIntegerField(default=2)
    ram = models.CharField(max_length=64, default='4G')
    gpu = models.CharField(max_length=64, default='none')
    env_defaults = models.JSONField(default=dict, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name
