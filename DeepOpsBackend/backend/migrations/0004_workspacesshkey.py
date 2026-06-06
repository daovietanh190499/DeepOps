import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0003_userdrive_workspace_mount'),
    ]

    operations = [
        migrations.CreateModel(
            name='WorkspaceSSHKey',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('public_key', models.TextField()),
                ('private_key_encrypted', models.TextField()),
                ('fingerprint', models.CharField(max_length=128)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('workspace', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='ssh_key', to='backend.workspace')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
