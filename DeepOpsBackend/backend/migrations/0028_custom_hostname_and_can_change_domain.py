from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0027_serverplantemplate_file_mounts'),
    ]

    operations = [
        migrations.AddField(
            model_name='resourcegroup',
            name='can_change_domain',
            field=models.BooleanField(
                default=False,
                help_text='Members may set a custom ingress hostname when creating or editing servers',
            ),
        ),
        migrations.AddField(
            model_name='workspace',
            name='custom_hostname',
            field=models.CharField(
                blank=True,
                help_text='Optional ingress hostname override; empty uses default slug-user.domain',
                max_length=253,
                null=True,
                unique=True,
            ),
        ),
    ]
