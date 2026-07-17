from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('backend', '0034_workspace_resource_limit_ratio'),
    ]

    operations = [
        migrations.CreateModel(
            name='WorkspaceCollaborator',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('can_start_stop', models.BooleanField(default=False)),
                ('can_edit', models.BooleanField(default=False)),
                ('can_delete', models.BooleanField(default=False)),
                ('can_manage_collaborators', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='workspace_collaborations', to='backend.user')),
                ('workspace', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='collaborators', to='backend.workspace')),
            ],
            options={
                'ordering': ['-updated_at'],
                'unique_together': {('workspace', 'user')},
            },
        ),
    ]

