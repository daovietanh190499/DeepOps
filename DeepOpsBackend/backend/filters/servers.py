import django_filters
from backend.models import Server

class ServerFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='iexact')

    class Meta:
        model = Server
        fields = '__all__'