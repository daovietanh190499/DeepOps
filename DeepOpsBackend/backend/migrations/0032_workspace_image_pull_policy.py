from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0031_drop_legacy_routing_artifacts'),
    ]

    operations = [
        migrations.AddField(
            model_name='workspace',
            name='image_pull_policy',
            field=models.CharField(
                choices=[
                    ('Always', 'Always'),
                    ('IfNotPresent', 'IfNotPresent'),
                    ('Never', 'Never'),
                ],
                default='IfNotPresent',
                help_text='Kubernetes imagePullPolicy for the main workspace container',
                max_length=32,
            ),
        ),
    ]
