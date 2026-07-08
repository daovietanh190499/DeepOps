from django.test import SimpleTestCase

from backend.models import User, UserDrive, Workspace
from backend.services.k8s_names import normalize_resource_username


class NormalizeResourceUsernameTests(SimpleTestCase):
    def test_lowercase_github_username(self):
        self.assertEqual(normalize_resource_username('DSLucas19'), 'dslucas19')

    def test_strips_invalid_chars(self):
        self.assertEqual(normalize_resource_username('User.Name'), 'user-name')

    def test_empty_fallback(self):
        self.assertEqual(normalize_resource_username(''), 'user')
        self.assertEqual(normalize_resource_username('---'), 'user')

    def test_leading_trailing_hyphen(self):
        self.assertEqual(normalize_resource_username('-alice-'), 'alice')


class ResourceUsernameInModelsTests(SimpleTestCase):
    def test_drive_claim_name(self):
        user = User(username='DSLucas19')
        drive = UserDrive(user=user, name='postgres', slug='opennote')
        self.assertEqual(
            drive.claim_name,
            'drive-dohub-dslucas19-opennote',
        )

    def test_workspace_release_name(self):
        user = User(username='DSLucas19')
        ws = Workspace(user=user, name='OpenNote', slug='opennote')
        self.assertEqual(ws.release_name, 'dohub-dslucas19-opennote')
        self.assertEqual(ws.default_hostname, 'opennote-dslucas19.dohub.com')
