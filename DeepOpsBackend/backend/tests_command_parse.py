from django.test import SimpleTestCase

from backend.services.command_parse import format_container_command, parse_container_command


class CommandParseTests(SimpleTestCase):
    def test_sh_c_single_quoted_script(self):
        raw = "sh -c 'redis-server --requirepass $PASSWORD --appendonly yes'"
        self.assertEqual(
            parse_container_command(raw),
            ['sh', '-c', 'redis-server --requirepass $PASSWORD --appendonly yes'],
        )

    def test_double_quoted_argument(self):
        raw = 'echo "hello world"'
        self.assertEqual(parse_container_command(raw), ['echo', 'hello world'])

    def test_list_passthrough(self):
        self.assertEqual(
            parse_container_command(['sh', '-c', 'redis-server']),
            ['sh', '-c', 'redis-server'],
        )

    def test_format_round_trip(self):
        parts = ['sh', '-c', 'redis-server --requirepass $PASSWORD --appendonly yes']
        self.assertEqual(
            parse_container_command(format_container_command(parts)),
            parts,
        )
