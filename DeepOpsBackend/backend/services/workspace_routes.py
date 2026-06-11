"""Path-based wstunnel routes on the hub domain (subdomain stays for the main app)."""

from backend.models import Workspace

from .k8s_env import DOMAIN_NAME

SSH_TUNNEL_SUFFIX = 'ssh-tunnel'
PORT_TUNNEL_SUFFIX = 'port-tunnel'


def sidecar_tunnel_path(username: str, slug: str, suffix: str) -> str:
    return f'/{username}/{slug}/{suffix}'


def sidecar_tunnel_path_prefix(username: str, slug: str, suffix: str) -> str:
    return f'{username}/{slug}/{suffix}'


def ssh_tunnel_ingress_path(workspace: Workspace) -> str:
    return sidecar_tunnel_path(workspace.user.username, workspace.slug, SSH_TUNNEL_SUFFIX)


def port_tunnel_ingress_path(workspace: Workspace) -> str:
    return sidecar_tunnel_path(workspace.user.username, workspace.slug, PORT_TUNNEL_SUFFIX)


def ssh_tunnel_path_prefix(workspace: Workspace) -> str:
    return sidecar_tunnel_path_prefix(workspace.user.username, workspace.slug, SSH_TUNNEL_SUFFIX)


def port_tunnel_path_prefix(workspace: Workspace) -> str:
    return sidecar_tunnel_path_prefix(workspace.user.username, workspace.slug, PORT_TUNNEL_SUFFIX)


def hub_wss_base_url() -> str:
    return f'wss://{DOMAIN_NAME}'


def ssh_tunnel_wss_url(workspace: Workspace) -> str:
    """Public route shown in UI; wstunnel client uses hub host + -P path prefix."""
    return f'{hub_wss_base_url()}{ssh_tunnel_ingress_path(workspace)}'


def port_tunnel_wss_url(workspace: Workspace) -> str:
    return f'{hub_wss_base_url()}{port_tunnel_ingress_path(workspace)}'
