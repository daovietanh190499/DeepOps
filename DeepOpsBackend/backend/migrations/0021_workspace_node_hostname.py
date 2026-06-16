from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0020_workspace_backup'),
    ]

    operations = [
        migrations.AddField(
            model_name='workspace',
            name='node_hostname',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Kubernetes node hostname to pin this workspace to (empty = auto schedule)',
                max_length=255,
            ),
        ),
    ]

