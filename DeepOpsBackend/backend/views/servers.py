from rest_framework.response import Response
from rest_framework import viewsets
from django_filters import rest_framework as filters

from backend.models import Server
from backend.serializers import ServerSerializer
from backend.paginations import CustomPagination
from backend.filters import ServerFilter

class ServerView(viewsets.ModelViewSet):
    serializer_class = ServerSerializer
    queryset = Server.objects.all()
    pagination_class = CustomPagination
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = ServerFilter
    
