from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0016_float_cpu'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='workspacedrivemount',
            unique_together={('workspace', 'mount_path')},
        ),
    ]
