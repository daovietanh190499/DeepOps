"""Per-workspace SSH key generation and secure storage."""

import base64
import hashlib

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from django.conf import settings

from backend.models import Workspace, WorkspaceSSHKey

from .k8s_env import DOMAIN_NAME
from .workspace_routes import (
    hub_wss_base_url,
    ssh_tunnel_ingress_path,
    ssh_tunnel_path_prefix,
    ssh_tunnel_wss_url,
)


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.SECRET_KEY.encode('utf-8')).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def public_key_fingerprint(public_openssh: str) -> str:
    parts = public_openssh.strip().split()
    if len(parts) < 2:
        return ''
    blob = base64.b64decode(parts[1])
    digest = hashlib.sha256(blob).digest()
    return 'SHA256:' + base64.b64encode(digest).decode('ascii').rstrip('=')


def _openssh_private_bytes(private_key: Ed25519PrivateKey) -> str:
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.OpenSSH,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode('utf-8')


def generate_host_key_openssh() -> str:
    return _openssh_private_bytes(Ed25519PrivateKey.generate())


def generate_keypair() -> tuple[str, str, str]:
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    private_openssh = _openssh_private_bytes(private_key)
    public_openssh = public_key.public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH,
    ).decode('utf-8')
    return public_openssh, private_openssh, public_key_fingerprint(public_openssh)


def encrypt_private_key(private_openssh: str) -> str:
    return _fernet().encrypt(private_openssh.encode('utf-8')).decode('ascii')


def decrypt_private_key(encrypted: str) -> str:
    return _fernet().decrypt(encrypted.encode('ascii')).decode('utf-8')


def ssh_secret_name(workspace: Workspace) -> str:
    return f'{workspace.user.username}-{workspace.slug}-ssh'


def ssh_user() -> str:
    return 'coder'


def wss_tunnel_url(workspace: Workspace) -> str:
    return ssh_tunnel_wss_url(workspace)


def wstunnel_proxy_command(workspace: Workspace) -> str:
    prefix = ssh_tunnel_path_prefix(workspace)
    return (
        f'wstunnel client --log-lvl=warn -P {prefix} '
        f'-L stdio://127.0.0.1:2222 {hub_wss_base_url()}'
    )


def ssh_config_snippet(workspace: Workspace, *, identity_path: str | None = None) -> str:
    host_alias = f'dohub-{workspace.slug}'
    key_path = identity_path or f'~/.ssh/dohub-{workspace.slug}'
    return '\n'.join([
        f'Host {host_alias}',
        f'    HostName {DOMAIN_NAME}',
        f'    User {ssh_user()}',
        f'    IdentityFile {key_path}',
        f'    ProxyCommand {wstunnel_proxy_command(workspace)}',
        '    StrictHostKeyChecking accept-new',
    ])


def ssh_connect_command(workspace: Workspace) -> str:
    return f'ssh dohub-{workspace.slug}'


def get_or_none(workspace: Workspace) -> WorkspaceSSHKey | None:
    return WorkspaceSSHKey.objects.filter(workspace=workspace).first()


def host_key_plaintext(record: WorkspaceSSHKey) -> str:
    if not record.host_key_encrypted:
        return ''
    return decrypt_private_key(record.host_key_encrypted)


def ensure_host_key_material(record: WorkspaceSSHKey) -> str:
    """Return ssh-bridge host private key, generating and persisting if needed."""
    existing = host_key_plaintext(record)
    if existing:
        return existing
    host_key = generate_host_key_openssh()
    record.host_key_encrypted = encrypt_private_key(host_key)
    record.save(update_fields=['host_key_encrypted', 'updated_at'])
    return host_key


def create_or_rotate_keys(workspace: Workspace) -> tuple[WorkspaceSSHKey, str]:
    """Returns (record, private_key_openssh plaintext for one-time download)."""
    public_key, private_key, fingerprint = generate_keypair()
    host_key = generate_host_key_openssh()
    record, _created = WorkspaceSSHKey.objects.update_or_create(
        workspace=workspace,
        defaults={
            'public_key': public_key.strip(),
            'private_key_encrypted': encrypt_private_key(private_key),
            'host_key_encrypted': encrypt_private_key(host_key),
            'fingerprint': fingerprint,
        },
    )
    return record, private_key


def ssh_info_payload(workspace: Workspace) -> dict:
    record = get_or_none(workspace)
    return {
        'has_key': record is not None,
        'fingerprint': record.fingerprint if record else '',
        'public_key': record.public_key if record else '',
        'ssh_user': ssh_user(),
        'wss_url': wss_tunnel_url(workspace),
        'path_prefix': ssh_tunnel_path_prefix(workspace),
        'ssh_host_alias': f'dohub-{workspace.slug}',
        'ssh_command': ssh_connect_command(workspace) if record else '',
        'ssh_config': ssh_config_snippet(workspace) if record else '',
        'proxy_command': wstunnel_proxy_command(workspace) if record else '',
        'proxy_hint': (
            'Install wstunnel: https://github.com/erebe/wstunnel/releases '
            f'(path {ssh_tunnel_ingress_path(workspace)} on {DOMAIN_NAME})'
        ),
    }
