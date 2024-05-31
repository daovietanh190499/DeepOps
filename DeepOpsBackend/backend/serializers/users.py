from rest_framework import serializers
from backend.models import User
from .servers import ServerSerializer

class UserSerializer(serializers.ModelSerializer):
    server = serializers.ListField(child=ServerSerializer())
    class Meta:
        model = User
        fields = '__all__'
    
    def update(self, instance, data):
        instance.status = data.get('status', instance.status)

class UserResponseSerializer(serializers.ModelSerializer):
    server = serializers.ListField(child=ServerSerializer())
    class Meta:
        model = User
        fields = '__all__'