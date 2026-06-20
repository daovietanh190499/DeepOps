"""Crypto helpers for managed SSH nodes (independent from workspace ssh-bridge)."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from django.conf import settings


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

