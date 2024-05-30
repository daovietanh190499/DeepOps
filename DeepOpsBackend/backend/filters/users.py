import django_filters
from backend.models import User

class UserFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='iexact')

    class Meta:
        model = User
        fields = '__all__'