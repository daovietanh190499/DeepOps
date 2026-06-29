from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0032_workspace_image_pull_policy'),
    ]

    operations = [
        migrations.AddField(
            model_name='workspace',
            name='init_container_enabled',
            field=models.BooleanField(
                default=False,
                help_text='Run a single user-defined initContainer before the main container',
            ),
        ),
        migrations.AddField(
            model_name='workspace',
            name='init_container_image_source',
            field=models.CharField(
                choices=[('main', 'main'), ('busybox', 'busybox')],
                default='busybox',
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name='workspace',
            name='init_container_command',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
