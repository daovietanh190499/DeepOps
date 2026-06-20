"""Hub-side routing helpers for sidecar wstunnel endpoints."""

from __future__ import annotations

import os

from backend.models import Workspace


def _domain_name() -> str:
    return os.environ.get('DOMAIN_NAME', 'dohub.com')


def hub_wss_base_url() -> str:
    return f'wss://{_domain_name()}'


def sidecar_tunnel_path(username: str, slug: str, suffix: str) -> str:
    return f'/{username}/{slug}/{suffix}'


def sidecar_tunnel_path_prefix(username: str, slug: str, suffix: str) -> str:
    # wstunnel expects the prefix WITHOUT the leading slash
    return sidecar_tunnel_path(username, slug, suffix).lstrip('/')


PORT_TUNNEL_SUFFIX = 'port-tunnel'


def port_tunnel_ingress_path(workspace: Workspace) -> str:
    return sidecar_tunnel_path(workspace.user.username, workspace.slug, PORT_TUNNEL_SUFFIX)


def port_tunnel_path_prefix(workspace: Workspace) -> str:
    return sidecar_tunnel_path_prefix(workspace.user.username, workspace.slug, PORT_TUNNEL_SUFFIX)


def port_tunnel_wss_url(workspace: Workspace) -> str:
    return f'{hub_wss_base_url()}{port_tunnel_ingress_path(workspace)}'

