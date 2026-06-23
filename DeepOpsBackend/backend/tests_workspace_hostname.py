from django.test import TestCase

from backend.models import User, Workspace
from backend.services.workspace_hostname import (
    normalize_custom_hostname,
    validate_custom_hostname,
    validate_custom_hostname_unique,
)


class WorkspaceHostnameTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='alice', is_accept=True)

    def test_default_hostname_uses_subdomain_pattern(self):
        import os
        prev = os.environ.get('DOMAIN_NAME')
        os.environ['DOMAIN_NAME'] = 'example.edu'
        try:
            ws = Workspace(user=self.user, name='Lab', slug='lab')
            self.assertEqual(ws.default_hostname, 'lab-alice.example.edu')
            self.assertEqual(ws.hostname, 'lab-alice.example.edu')
        finally:
            if prev is None:
                os.environ.pop('DOMAIN_NAME', None)
            else:
                os.environ['DOMAIN_NAME'] = prev

    def test_custom_hostname_overrides_default(self):
        ws = Workspace(
            user=self.user,
            name='Lab',
            slug='lab',
            custom_hostname='my-server.example.edu',
        )
        self.assertEqual(ws.hostname, 'my-server.example.edu')

    def test_custom_hostname_normalizes_case_and_trailing_dot(self):
        ws = Workspace(
            user=self.user,
            name='Lab',
            slug='lab',
            custom_hostname='My-Server.Example.Edu.',
        )
        self.assertEqual(ws.hostname, 'my-server.example.edu')

    def test_validate_custom_hostname_rejects_invalid(self):
        self.assertIsNotNone(validate_custom_hostname('not a host'))
        self.assertIsNotNone(validate_custom_hostname(''))
        self.assertIsNone(validate_custom_hostname('valid.example.com'))

    def test_validate_custom_hostname_unique(self):
        existing = Workspace.objects.create(
            user=self.user,
            name='One',
            slug='one',
            custom_hostname='shared.example.com',
        )
        self.assertEqual(
            validate_custom_hostname_unique('shared.example.com'),
            'hostname already in use by another server',
        )
        self.assertIsNone(
            validate_custom_hostname_unique('shared.example.com', workspace_id=existing.pk),
        )

    def test_normalize_custom_hostname(self):
        self.assertEqual(
            normalize_custom_hostname(' Host.Example.Com. '),
            'host.example.com',
        )
