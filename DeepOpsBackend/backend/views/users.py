from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from django_filters import rest_framework as filters
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from django.db import transaction


from backend.models import User
from backend.serializers import UserSerializer, UserResponseSerializer, UserRequestSerializer
from backend.filters import UserFilter
from backend.tasks import create_server_task, terminate_server_task

class UserView(viewsets.ModelViewSet):
    parser_classes = (MultiPartParser,)
    serializer_class = UserSerializer
    queryset = User.objects.all()
    filterset_class = UserFilter
    ordering_fields = ['username']
    ordering = "-username"

    @transaction.atomic
    @extend_schema(request=UserRequestSerializer, responses=UserResponseSerializer, methods=['POST'])
    def create(self, request, *args, **kwargs) -> Response:
        user_serializer = UserRequestSerializer(data=request.data)
        if user_serializer.is_valid():
            user_serializer.save()
            return Response(UserResponseSerializer(user_serializer.instance).data)
        else:
            return Response(user_serializer.errors)

    @extend_schema(request=None, responses=UserResponseSerializer, methods=['POST'])
    @action(detail=True, url_name="create_server", methods=['post'])
    def create_server(self, request, pk=None) -> Response:
        user = get_object_or_404(User, pk=pk)
        user_serializer = UserSerializer(user)
        task = create_server_task.delay(user=user_serializer.data)
        return Response(user_serializer.data)

    @extend_schema(request=None, responses=UserResponseSerializer, methods=['POST'])
    @action(detail=True, url_name="terminate_server", methods=['post'])
    def terminate_server(self, request, pk=None) -> Response:
        user = get_object_or_404(User, pk=pk)
        user_serializer = UserSerializer(user)
        task = terminate_server_task.delay(user=user_serializer.data)
        return Response(user_serializer.data)