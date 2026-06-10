from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0015_env_template_placeholders'),
    ]

    operations = [
        migrations.AlterField(
            model_name='workspace',
            name='cpu',
            field=models.FloatField(default=2),
        ),
        migrations.AlterField(
            model_name='serverplantemplate',
            name='cpu',
            field=models.FloatField(default=2),
        ),
    ]
