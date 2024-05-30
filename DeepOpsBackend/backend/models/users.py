from django.db import models
from .servers import Server

ROLE_CHOICES = (
    ("admin", "admin"),
    ("normal", "normal")
)

STATES = (
    ("terminated", "terminated"),
    ("creating", "creating"),
    ("running", "running"),
    ("terminating", "terminating")
)

class User(models.Model):
    github_access_token = models.CharField(max_length=200)
    github_id = models.CharField(max_length=50)
    username = models.CharField(max_length=50)
    avatar = models.CharField(max_length=200)
    is_accept = models.BooleanField(default=False)
    inferencing_server = models.ForeignKey(to=Server, on_delete=models.CASCADE, related_name="inferencing_server")
    servers = models.ManyToManyField(to=Server, related_name="server_set")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='normal')
    state = models.CharField(max_length=50, choices=STATES, default='terminated')
    password = models.CharField(max_length=100)
    last_activity = models.DateTimeField(auto_now=True)
