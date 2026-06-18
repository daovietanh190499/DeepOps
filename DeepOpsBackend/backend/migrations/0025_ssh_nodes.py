import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0024_workspace_exec_shell'),
    ]

    operations = [
        migrations.CreateModel(
            name='SSHNodeManagerKey',
            fields=[
                ('id', models.PositiveSmallIntegerField(default=1, primary_key=True, serialize=False)),
                ('public_key', models.TextField()),
                ('encrypted_private_key', models.TextField()),
                ('fingerprint', models.CharField(blank=True, default='', max_length=128)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'SSH node manager key',
            },
        ),
        migrations.CreateModel(
            name='SSHNode',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('label', models.CharField(blank=True, default='', max_length=255)),
                ('host', models.CharField(max_length=255)),
                ('port', models.PositiveIntegerField(default=22)),
                ('username', models.CharField(max_length=128)),
                ('status', models.CharField(
                    choices=[
                        ('unknown', 'Unknown'),
                        ('checking', 'Checking'),
                        ('online', 'Online'),
                        ('offline', 'Offline'),
                    ],
                    default='unknown',
                    max_length=16,
                )),
                ('health_line', models.TextField(blank=True, default='')),
                ('last_error', models.TextField(blank=True, default='')),
                ('last_checked_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-updated_at'],
            },
        ),
    ]
