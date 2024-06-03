from rest_framework import serializers
from backend.models import User
from .servers import ServerSerializer

class UserSerializer(serializers.ModelSerializer):
    servers = ServerSerializer(many=True)
    inferencing_server = ServerSerializer()
    class Meta:
        model = User
        fields = '__all__'
    
    def update(self, instance, data):
        instance.status = data.get('status', instance.status)

class UserRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        exclude = ['inferencing_server', 'servers']

class UserResponseSerializer(serializers.ModelSerializer):
    servers = serializers.ListField(child=ServerSerializer())
    inferencing_server = ServerSerializer()
    class Meta:
        model = User
        fields = '__all__'