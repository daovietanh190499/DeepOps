from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0010_vgpu_catalog'),
    ]

    operations = [
        migrations.AddField(
            model_name='resourcegroup',
            name='can_change_privileged',
            field=models.BooleanField(
                default=False,
                help_text='Members may enable privileged (root) pods when creating servers',
            ),
        ),
        migrations.AddField(
            model_name='workspace',
            name='privileged',
            field=models.BooleanField(
                default=True,
                help_text='Run code-server container with securityContext.privileged=true',
            ),
        ),
        migrations.AlterField(
            model_name='workspace',
            name='privileged',
            field=models.BooleanField(
                default=False,
                help_text='Run code-server container with securityContext.privileged=true',
            ),
        ),
    ]
