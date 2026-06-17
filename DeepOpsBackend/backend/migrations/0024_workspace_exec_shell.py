from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0023_resourcegroup_max_images'),
    ]

    operations = [
        migrations.AddField(
            model_name='workspace',
            name='exec_shell',
            field=models.CharField(
                choices=[('bash', 'bash'), ('sh', 'sh')],
                default='bash',
                help_text='Shell used by SSH bridge kubectl exec (bash or sh)',
                max_length=16,
            ),
        ),
    ]
