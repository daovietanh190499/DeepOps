from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0033_workspace_init_container'),
    ]

    operations = [
        migrations.AddField(
            model_name='workspace',
            name='resource_limit_ratio',
            field=models.FloatField(
                default=1.5,
                help_text='Multiplier from CPU/RAM request to Kubernetes limit (1 or 1.5)',
            ),
        ),
    ]
