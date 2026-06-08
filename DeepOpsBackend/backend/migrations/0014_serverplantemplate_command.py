from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0013_serverplantemplate_docker_ports'),
    ]

    operations = [
        migrations.AddField(
            model_name='serverplantemplate',
            name='container_command',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
