import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0005_workspacesshkey_host_key'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='email',
            field=models.EmailField(blank=True, default='', max_length=254),
        ),
        migrations.CreateModel(
            name='ResourceGroup',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=128, unique=True)),
                ('max_cpu', models.PositiveIntegerField()),
                ('max_ram_g', models.PositiveIntegerField()),
                ('max_drive_size_gi', models.PositiveIntegerField()),
                ('max_gpu_vram_g', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='ResourceGroupMember',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='members', to='backend.resourcegroup')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='resource_group_membership', to='backend.user')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
