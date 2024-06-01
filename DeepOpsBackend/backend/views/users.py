from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework.decorators import action
from django_filters import rest_framework as filters

from backend.models import User
from backend.serializers import UserSerializer, UserResponseSerializer
from backend.filters import UserFilter
from backend.tasks import create_server_task, terminate_server_task

class UserView(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    filterset_class = UserFilter

    @action(detail=True, url_name="create_server", methods=['post'])
    def create_server(self, request, pk=None) -> Response:
        create_server_task()

    @action(detail=True, url_name="terminate_server", methods=['post'])
    def terminate_server(self, request, pk=None) -> Response:
        terminate_server_task()