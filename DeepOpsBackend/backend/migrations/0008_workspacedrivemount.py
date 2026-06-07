import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0007_resource_group_counts'),
    ]

    operations = [
        migrations.CreateModel(
            name='WorkspaceDriveMount',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('mount_path', models.CharField(max_length=256)),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user_drive', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='extra_workspace_mounts', to='backend.userdrive')),
                ('workspace', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='extra_drive_mounts', to='backend.workspace')),
            ],
            options={
                'ordering': ['sort_order', 'created_at'],
                'unique_together': {('workspace', 'mount_path'), ('workspace', 'user_drive')},
            },
        ),
    ]
