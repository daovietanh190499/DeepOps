from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0006_resource_groups'),
    ]

    operations = [
        migrations.AddField(
            model_name='resourcegroup',
            name='max_drives',
            field=models.PositiveIntegerField(default=0, help_text='Max drives per member; 0 = unlimited'),
        ),
        migrations.AddField(
            model_name='resourcegroup',
            name='max_servers',
            field=models.PositiveIntegerField(default=0, help_text='Max servers (workspaces) per member; 0 = unlimited'),
        ),
    ]
