from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0004_workspacesshkey'),
    ]

    operations = [
        migrations.AddField(
            model_name='workspacesshkey',
            name='host_key_encrypted',
            field=models.TextField(blank=True, default=''),
        ),
    ]
