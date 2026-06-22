from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0028_custom_hostname_and_can_change_domain'),
    ]

    operations = [
        migrations.DeleteModel(
            name='WorkspaceSSHKey',
        ),
    ]
