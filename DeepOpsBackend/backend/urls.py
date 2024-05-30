from django.urls import path, include
from rest_framework import routers
import backend.views as views

router = routers.DefaultRouter()

router.register(r'server', views.ServerView, basename='servers')
router.register(r'user', views.UserView, basename='users')

urlpatterns = [
    path('api/', include(router.urls)),
]