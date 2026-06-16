import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0021_workspace_node_hostname'),
    ]

    operations = [
        migrations.AddField(
            model_name='dockerimage',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='dockerimage',
            name='created_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='docker_images',
                to='backend.user',
            ),
        ),
        migrations.AddField(
            model_name='dockerimage',
            name='is_accepted',
            field=models.BooleanField(
                default=True,
                help_text='User-submitted images require admin acceptance before use in servers',
            ),
        ),
    ]
