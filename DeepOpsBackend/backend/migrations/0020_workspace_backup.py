from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0019_workspace_ws_tunnel_ports'),
    ]

    operations = [
        migrations.AddField(
            model_name='workspace',
            name='backup_enabled',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='workspace',
            name='backup_folders',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='workspace',
            name='backup_rclone_config',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='workspace',
            name='backup_remote',
            field=models.CharField(blank=True, default='', max_length=512),
        ),
        migrations.AddField(
            model_name='workspace',
            name='backup_schedule',
            field=models.CharField(blank=True, default='', max_length=128),
        ),
    ]
