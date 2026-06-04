from django.urls import path

from backend import views
from backend.views import workspaces as ws_views

urlpatterns = [
    path('', views.index, name='index'),
    path('github-callback', views.github_callback, name='github-callback'),
    path('login', views.login, name='login'),
    path('logout', views.logout, name='logout'),
    path('user_state', views.user_state, name='user-state'),
    path('all_users', views.all_users, name='all-users'),
    path('accept_user/<str:username>', views.accept_user, name='accept-user'),
    path('delete_user/<str:username>', views.delete_user, name='delete-user'),
    path('change_role/<str:username>/<str:role>', views.change_role, name='change-role'),

    path('docker_images', ws_views.docker_images_list, name='docker-images'),
    path('workspaces/run', ws_views.workspace_run, name='workspace-run'),
    path('workspaces/bulk_run', ws_views.workspace_bulk_run, name='workspace-bulk-run'),
    path('workspaces/create', ws_views.workspace_create, name='workspace-create'),
    path('workspaces/<uuid:workspace_id>/export', ws_views.workspace_export, name='workspace-export'),
    path('workspaces/<uuid:workspace_id>/start', ws_views.workspace_start, name='workspace-start'),
    path('workspaces/<uuid:workspace_id>/stop', ws_views.workspace_stop, name='workspace-stop'),
    path('workspaces/<uuid:workspace_id>', ws_views.workspace_detail, name='workspace-detail'),
    path('workspaces', ws_views.my_workspaces, name='my-workspaces'),

    path('admin/workspaces', ws_views.admin_workspaces, name='admin-workspaces'),
    path('admin/docker_images', ws_views.admin_docker_images, name='admin-docker-images'),
    path('admin/docker_images/create', ws_views.admin_docker_image_create, name='admin-docker-image-create'),
    path('admin/docker_images/<int:image_id>', ws_views.admin_docker_image_detail, name='admin-docker-image-detail'),
]
