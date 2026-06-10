from django.db import migrations, models

import backend.models.platform


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0017_drive_multi_mount_paths'),
    ]

    operations = [
        migrations.AddField(
            model_name='serverplantemplate',
            name='drive_mounts',
            field=models.JSONField(
                blank=True,
                default=backend.models.platform._default_drive_mounts,
                help_text='Default mount paths, e.g. [{"mount_path": "/app/data"}]',
            ),
        ),
    ]
