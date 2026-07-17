from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('backend', '0035_workspace_collaborators'),
    ]

    operations = [
        migrations.AddField(
            model_name='workspacecollaborator',
            name='can_terminal',
            field=models.BooleanField(default=False),
        ),
    ]

