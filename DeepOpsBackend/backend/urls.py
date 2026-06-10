from django.urls import path

from backend import views
from backend.views import catalog as catalog_views
from backend.views import cluster as cluster_views
from backend.views import drives as drive_views
from backend.views import groups as group_views
from backend.views import ssh as ssh_views
from backend.views import workspaces as ws_views

urlpatterns = [
    path('', views.index, name='index'),
    path('github-callback', views.github_callback, name='github-callback'),
    path('login', views.login, name='login'),
    path('logout', views.logout, name='logout'),
    path('user_state', views.user_state, name='user-state'),
    path('all_users', views.all_users, name='all-users'),
    path('admin/users/search', group_views.admin_user_search, name='admin-user-search'),
    path('admin/resource_groups', group_views.admin_resource_groups, name='admin-resource-groups'),
    path('admin/resource_groups/create', group_views.admin_resource_group_create, name='admin-resource-group-create'),
    path('admin/resource_groups/<uuid:group_id>', group_views.admin_resource_group_detail, name='admin-resource-group-detail'),
    path('admin/resource_groups/<uuid:group_id>/update', group_views.admin_resource_group_update, name='admin-resource-group-update'),
    path('admin/resource_groups/<uuid:group_id>/members', group_views.admin_resource_group_add_member, name='admin-resource-group-add-member'),
    path('admin/resource_groups/<uuid:group_id>/members/bulk', group_views.admin_resource_group_bulk_add_members, name='admin-resource-group-bulk-add'),
    path('admin/resource_groups/<uuid:group_id>/members/<int:member_user_id>', group_views.admin_resource_group_remove_member, name='admin-resource-group-remove-member'),
    path('accept_user/<str:username>', views.accept_user, name='accept-user'),
    path('delete_user/<str:username>', views.delete_user, name='delete-user'),
    path('change_role/<str:username>/<str:role>', views.change_role, name='change-role'),

    path('drives', drive_views.my_drives, name='my-drives'),
    path('drives/status', drive_views.my_drives_status, name='my-drives-status'),
    path('drives/create', drive_views.drive_create, name='drive-create'),
    path('drives/bulk_create', drive_views.drive_bulk_create, name='drive-bulk-create'),
    path('drives/<uuid:drive_id>', drive_views.drive_delete, name='drive-delete'),
    path('admin/cluster/overview', cluster_views.admin_cluster_overview, name='admin-cluster-overview'),
    path('admin/cluster/join-command', cluster_views.admin_cluster_join_command, name='admin-cluster-join'),
    path('admin/cluster/directpv/discover', cluster_views.admin_directpv_discover, name='admin-directpv-discover'),
    path('admin/cluster/directpv/discover/run', cluster_views.admin_directpv_discover_run, name='admin-directpv-discover-run'),
    path('admin/cluster/directpv/discover/save', cluster_views.admin_directpv_discover_save, name='admin-directpv-discover-save'),
    path('admin/cluster/directpv/init', cluster_views.admin_directpv_init, name='admin-directpv-init'),
    path('admin/drives', drive_views.admin_drives, name='admin-drives'),
    path('admin/drives/status', drive_views.admin_drives_status, name='admin-drives-status'),

    path('platform/catalog', catalog_views.platform_catalog, name='platform-catalog'),
    path('admin/platform/catalog', catalog_views.admin_platform_catalog, name='admin-platform-catalog'),
    path('admin/platform/options', catalog_views.admin_platform_option_create, name='admin-platform-option-create'),
    path('admin/platform/options/<int:option_id>', catalog_views.admin_platform_option_detail, name='admin-platform-option-detail'),
    path('admin/platform/templates', catalog_views.admin_platform_template_create, name='admin-platform-template-create'),
    path('admin/platform/templates/<int:template_id>', catalog_views.admin_platform_template_detail, name='admin-platform-template-detail'),
    path('docker_images', ws_views.docker_images_list, name='docker-images'),
    path('workspaces/run', ws_views.workspace_run, name='workspace-run'),
    path('workspaces/bulk_run', ws_views.workspace_bulk_run, name='workspace-bulk-run'),
    path('workspaces/create', ws_views.workspace_create, name='workspace-create'),
    path('workspaces/<uuid:workspace_id>/ssh/generate', ssh_views.workspace_ssh_generate, name='workspace-ssh-generate'),
    path('workspaces/<uuid:workspace_id>/ssh/download', ssh_views.workspace_ssh_download_key, name='workspace-ssh-download'),
    path('workspaces/<uuid:workspace_id>/ssh', ssh_views.workspace_ssh_info, name='workspace-ssh-info'),
    path('workspaces/<uuid:workspace_id>/logs', ws_views.workspace_logs_view, name='workspace-logs'),
    path('workspaces/<uuid:workspace_id>/describe', ws_views.workspace_describe_view, name='workspace-describe'),
    path('workspaces/<uuid:workspace_id>/export', ws_views.workspace_export, name='workspace-export'),
    path('workspaces/<uuid:workspace_id>/start', ws_views.workspace_start, name='workspace-start'),
    path('workspaces/<uuid:workspace_id>/stop', ws_views.workspace_stop, name='workspace-stop'),
    path('workspaces/<uuid:workspace_id>', ws_views.workspace_detail, name='workspace-detail'),
    path('workspaces', ws_views.my_workspaces, name='my-workspaces'),
    path('workspaces/status', ws_views.my_workspaces_status, name='my-workspaces-status'),

    path('admin/workspaces', ws_views.admin_workspaces, name='admin-workspaces'),
    path('admin/workspaces/status', ws_views.admin_workspaces_status, name='admin-workspaces-status'),
    path('admin/docker_images', ws_views.admin_docker_images, name='admin-docker-images'),
    path('admin/docker_images/create', ws_views.admin_docker_image_create, name='admin-docker-image-create'),
    path('admin/docker_images/<int:image_id>', ws_views.admin_docker_image_detail, name='admin-docker-image-detail'),
]
