from django.test import SimpleTestCase

from backend.services.env_templates import expand_env_template_value, expand_env_vars


class EnvTemplateTests(SimpleTestCase):
    def test_username_placeholder(self):
        self.assertEqual(
            expand_env_template_value('user-<<username>>', 'alice'),
            'user-alice',
        )

    def test_username_in_env_vars(self):
        self.assertEqual(
            expand_env_vars({'OWNER': '<<username>>'}, 'bob'),
            {'OWNER': 'bob'},
        )
