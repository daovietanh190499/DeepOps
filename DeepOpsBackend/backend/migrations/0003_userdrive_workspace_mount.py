import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0002_workspace_dockerimage'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserDrive',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=128)),
                ('slug', models.SlugField(max_length=48)),
                ('size', models.CharField(default='20Gi', max_length=32)),
                ('status', models.CharField(
                    choices=[('pending', 'pending'), ('bound', 'bound'), ('lost', 'lost')],
                    default='pending',
                    max_length=32,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='drives',
                    to='backend.user',
                )),
            ],
            options={
                'ordering': ['-created_at'],
                'unique_together': {('user', 'slug')},
            },
        ),
        migrations.AddField(
            model_name='workspace',
            name='mount_path',
            field=models.CharField(default='/home/coder', max_length=256),
        ),
        migrations.AddField(
            model_name='workspace',
            name='user_drive',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='workspaces',
                to='backend.userdrive',
            ),
        ),
        migrations.RemoveField(
            model_name='workspace',
            name='drive',
        ),
    ]
