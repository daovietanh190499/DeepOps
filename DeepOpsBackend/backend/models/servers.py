from django.db import models


class ServerOption(models.Model):
    name = models.CharField(max_length=255, unique=True)
    image = models.CharField(max_length=255, default='logo.png')
    docker_image = models.CharField(max_length=255, default='codercom/code-server')
    cpu = models.PositiveIntegerField(default=2)
    ram = models.CharField(max_length=64, default='4G')
    drive = models.CharField(max_length=64, default='30TB')
    gpu = models.CharField(max_length=255, blank=True, default='')
    color = models.CharField(max_length=32, default='#fcb040')

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.name
