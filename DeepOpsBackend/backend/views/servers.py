from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework.parsers import MultiPartParser
from django_filters import rest_framework as filters
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from django.db import transaction


from backend.models import Server
from backend.serializers import ServerSerializer
from backend.filters import ServerFilter

class ServerView(viewsets.ModelViewSet):
    parser_classes = (MultiPartParser,)
    serializer_class = ServerSerializer
    queryset = Server.objects.all()
    filterset_class = ServerFilter
    ordering_fields = ['name', 'cpu']
    ordering = "-cpu"
    
