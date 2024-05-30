from django.db import models

class Server(models.Model):
    name = models.CharField(max_length=50)
    image = models.CharField(max_length=50)
    docker_image = models.CharField(max_length=50)
    docker_tag = models.CharField(max_length=50)
    cpu = models.CharField(max_length=50)
    ram = models.CharField(max_length=50)
    drive = models.CharField(max_length=50)
    gpu = models.CharField(max_length=100)
    color = models.CharField(max_length=10)
    