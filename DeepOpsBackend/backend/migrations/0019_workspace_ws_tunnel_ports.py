from django.db import migrations, models

import backend.models.workspaces


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0018_serverplantemplate_drive_mounts'),
    ]

    operations = [
        migrations.AddField(
            model_name='workspace',
            name='ws_tunnel_ports',
            field=models.JSONField(
                blank=True,
                default=backend.models.workspaces._default_ws_tunnel_ports,
                help_text='Main-container TCP ports exposed via wstunnel sidecar',
            ),
        ),
    ]
