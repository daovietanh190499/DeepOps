from rest_framework.response import Response
from rest_framework import viewsets
from django_filters import rest_framework as filters

from backend.models import Server
from backend.serializers import ServerSerializer
from backend.filters import ServerFilter

class ServerView(viewsets.ModelViewSet):
    serializer_class = ServerSerializer
    queryset = Server.objects.all()
    filterset_class = ServerFilter
    ordering_fields = ['name', 'cpu']
    ordering = "-cpu"
    
