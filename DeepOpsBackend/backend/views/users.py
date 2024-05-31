from rest_framework.response import Response
from rest_framework import viewsets
from django_filters import rest_framework as filters

from backend.models import User
from backend.serializers import UserSerializer, UserResponseSerializer
from backend.filters import UserFilter

class UserView(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    filterset_class = UserFilter