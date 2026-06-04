import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='DockerImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(max_length=255)),
                ('repository', models.CharField(max_length=512)),
                ('default_tag', models.CharField(default='latest', max_length=128)),
                ('is_active', models.BooleanField(default=True)),
                ('sort_order', models.PositiveIntegerField(default=0)),
            ],
            options={
                'ordering': ['sort_order', 'label'],
            },
        ),
        migrations.CreateModel(
            name='Workspace',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=128)),
                ('slug', models.SlugField(max_length=48)),
                ('cpu', models.PositiveIntegerField(default=2)),
                ('ram', models.CharField(default='4G', max_length=64)),
                ('drive', models.CharField(default='20Gi', max_length=64)),
                ('gpu', models.CharField(blank=True, default='', max_length=255)),
                ('docker_repository', models.CharField(default='codercom/code-server', max_length=512)),
                ('docker_tag', models.CharField(default='4.89.0-ubuntu', max_length=128)),
                ('env_vars', models.JSONField(blank=True, default=dict)),
                ('exposed_ports', models.JSONField(blank=True, default=list)),
                ('container_command', models.JSONField(blank=True, default=list)),
                ('state', models.CharField(
                    choices=[
                        ('offline', 'offline'),
                        ('running', 'running'),
                        ('pending_start', 'pending_start'),
                        ('pending_stop', 'pending_stop'),
                    ],
                    default='offline',
                    max_length=32,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='workspaces',
                    to='backend.user',
                )),
            ],
            options={
                'ordering': ['-updated_at'],
                'unique_together': {('user', 'slug')},
            },
        ),
    ]
