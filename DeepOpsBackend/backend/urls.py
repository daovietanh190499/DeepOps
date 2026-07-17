from django.urls import path, re_path

from backend import views
from backend.views import backup as backup_views
from backend.views import catalog as catalog_views
from backend.views import cluster as cluster_views
from backend.views import drives as drive_views
from backend.views import groups as group_views
from backend.views import ssh_nodes as ssh_nodes_views
from backend.views import tunnel as tunnel_views
from backend.views import workspaces as ws_views
from backend.views import nodes as nodes_views
from backend.views import users_search as users_search_views

urlpatterns = [
    path('', views.index, name='index'),
    path('github-callback', views.github_callback, name='github-callback'),
    path('login', views.login, name='login'),
    path('logout', views.logout, name='logout'),
    path('user_state', views.user_state, name='user-state'),
    path('all_users', views.all_users, name='all-users'),
    path('users/search', users_search_views.users_search, name='users-search'),
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
    path('cluster/resources_usage', cluster_views.cluster_resources_usage, name='cluster-resources-usage'),
    path('admin/cluster/join-command', cluster_views.admin_cluster_join_command, name='admin-cluster-join'),
    path('admin/cluster/directpv/discover', cluster_views.admin_directpv_discover, name='admin-directpv-discover'),
    path('admin/cluster/directpv/discover/run', cluster_views.admin_directpv_discover_run, name='admin-directpv-discover-run'),
    path('admin/cluster/directpv/discover/save', cluster_views.admin_directpv_discover_save, name='admin-directpv-discover-save'),
    path('admin/cluster/directpv/init', cluster_views.admin_directpv_init, name='admin-directpv-init'),
    path('admin/ssh-nodes/key', ssh_nodes_views.admin_ssh_node_key, name='admin-ssh-node-key'),
    path('admin/ssh-nodes/key/regenerate', ssh_nodes_views.admin_ssh_node_key_regenerate, name='admin-ssh-node-key-regenerate'),
    path('admin/ssh-nodes/refresh', ssh_nodes_views.admin_ssh_nodes_refresh, name='admin-ssh-nodes-refresh'),
    path('admin/ssh-nodes/create', ssh_nodes_views.admin_ssh_node_create, name='admin-ssh-node-create'),
    path('admin/ssh-nodes/<uuid:node_id>/refresh', ssh_nodes_views.admin_ssh_node_refresh, name='admin-ssh-node-refresh'),
    path('admin/ssh-nodes/<uuid:node_id>', ssh_nodes_views.admin_ssh_node_detail, name='admin-ssh-node-detail'),
    path('admin/ssh-nodes', ssh_nodes_views.admin_ssh_nodes, name='admin-ssh-nodes'),
    path('admin/drives', drive_views.admin_drives, name='admin-drives'),
    path('admin/drives/status', drive_views.admin_drives_status, name='admin-drives-status'),

    path('platform/catalog', catalog_views.platform_catalog, name='platform-catalog'),
    path('admin/platform/catalog', catalog_views.admin_platform_catalog, name='admin-platform-catalog'),
    path('admin/platform/options', catalog_views.admin_platform_option_create, name='admin-platform-option-create'),
    path('admin/platform/options/<int:option_id>', catalog_views.admin_platform_option_detail, name='admin-platform-option-detail'),
    path('admin/platform/templates', catalog_views.admin_platform_template_create, name='admin-platform-template-create'),
    path('admin/platform/templates/export', catalog_views.admin_platform_templates_export, name='admin-platform-templates-export'),
    path('admin/platform/templates/import', catalog_views.admin_platform_templates_import, name='admin-platform-templates-import'),
    path('admin/platform/templates/<int:template_id>', catalog_views.admin_platform_template_detail, name='admin-platform-template-detail'),
    path('docker_images', ws_views.docker_images_list, name='docker-images'),
    path('docker_images/mine', ws_views.my_docker_images, name='my-docker-images'),
    path('docker_images/create', ws_views.docker_image_create, name='docker-image-create'),
    path('docker_images/<int:image_id>', ws_views.docker_image_delete, name='docker-image-delete'),
    path('k8s/nodes', nodes_views.k8s_nodes, name='k8s-nodes'),
    path('workspaces/run', ws_views.workspace_run, name='workspace-run'),
    path('workspaces/bulk_run', ws_views.workspace_bulk_run, name='workspace-bulk-run'),
    path('workspaces/create', ws_views.workspace_create, name='workspace-create'),
    path('workspaces/<uuid:workspace_id>/tunnel/expose', tunnel_views.workspace_tunnel_expose, name='workspace-tunnel-expose'),
    path('workspaces/<uuid:workspace_id>/tunnel', tunnel_views.workspace_tunnel_info, name='workspace-tunnel-info'),
    path('workspaces/<uuid:workspace_id>/logs', ws_views.workspace_logs_view, name='workspace-logs'),
    path('workspaces/<uuid:workspace_id>/describe', ws_views.workspace_describe_view, name='workspace-describe'),
    path('workspaces/<uuid:workspace_id>/monitor/download', ws_views.workspace_monitor_download_view, name='workspace-monitor-download'),
    path('workspaces/<uuid:workspace_id>/monitor', ws_views.workspace_monitor_view, name='workspace-monitor'),
    path('workspaces/<uuid:workspace_id>/backup/run', backup_views.workspace_backup_run, name='workspace-backup-run'),
    path('workspaces/<uuid:workspace_id>/backup/stop', backup_views.workspace_backup_stop_view, name='workspace-backup-stop'),
    path('workspaces/<uuid:workspace_id>/backup/rclone/save', backup_views.workspace_backup_save_config, name='workspace-backup-rclone-save'),
    path('workspaces/<uuid:workspace_id>/backup/rclone/download', backup_views.workspace_backup_download_config, name='workspace-backup-rclone-download'),
    path('workspaces/<uuid:workspace_id>/backup/schedule', backup_views.workspace_backup_schedule, name='workspace-backup-schedule'),
    path('workspaces/<uuid:workspace_id>/backup', backup_views.workspace_backup_info, name='workspace-backup-info'),
    path('workspaces/<uuid:workspace_id>/export', ws_views.workspace_export, name='workspace-export'),
    path('workspaces/<uuid:workspace_id>/start', ws_views.workspace_start, name='workspace-start'),
    path('workspaces/<uuid:workspace_id>/stop', ws_views.workspace_stop, name='workspace-stop'),
    path('workspaces/<uuid:workspace_id>/collaborators/<int:collaborator_user_id>', ws_views.workspace_collaborator_detail, name='workspace-collaborator-detail'),
    path('workspaces/<uuid:workspace_id>/collaborators', ws_views.workspace_collaborators, name='workspace-collaborators'),
    path('workspaces/<uuid:workspace_id>', ws_views.workspace_detail, name='workspace-detail'),
    path('workspaces', ws_views.my_workspaces, name='my-workspaces'),
    path('workspaces/status', ws_views.my_workspaces_status, name='my-workspaces-status'),

    path('admin/workspaces', ws_views.admin_workspaces, name='admin-workspaces'),
    path('admin/workspaces/status', ws_views.admin_workspaces_status, name='admin-workspaces-status'),
    path('admin/docker_images', ws_views.admin_docker_images, name='admin-docker-images'),
    path('admin/docker_images/create', ws_views.admin_docker_image_create, name='admin-docker-image-create'),
    path('admin/docker_images/<int:image_id>', ws_views.admin_docker_image_detail, name='admin-docker-image-detail'),
    path('admin/docker_images/export', ws_views.admin_docker_images_export, name='admin-docker-images-export'),
    path('admin/docker_images/import', ws_views.admin_docker_images_import, name='admin-docker-images-import'),

    # Unknown paths → custom 404 (must stay last; excludes /static/ and /ws/)
    re_path(r'^(?!static/|ws/).*$', views.page_not_found, name='page-not-found'),
]
