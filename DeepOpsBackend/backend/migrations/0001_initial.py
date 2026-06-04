from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='ServerOption',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('image', models.CharField(default='logo.png', max_length=255)),
                ('docker_image', models.CharField(default='codercom/code-server', max_length=255)),
                ('cpu', models.PositiveIntegerField(default=2)),
                ('ram', models.CharField(default='4G', max_length=64)),
                ('drive', models.CharField(default='30TB', max_length=64)),
                ('gpu', models.CharField(blank=True, default='', max_length=255)),
                ('color', models.CharField(default='#fcb040', max_length=32)),
            ],
            options={'ordering': ['id']},
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('github_access_token', models.CharField(blank=True, default='', max_length=255)),
                ('github_id', models.BigIntegerField(blank=True, null=True)),
                ('username', models.CharField(max_length=255, unique=True)),
                ('image', models.TextField(blank=True, default='')),
                ('access_key', models.CharField(blank=True, default='', max_length=255)),
                ('server_ip', models.CharField(blank=True, default='', max_length=64)),
                ('role', models.CharField(choices=[('admin', 'admin'), ('normal_user', 'normal_user')], default='normal_user', max_length=32)),
                ('is_accept', models.BooleanField(default=False)),
                ('state', models.CharField(choices=[('offline', 'offline'), ('running', 'running'), ('pending_start', 'pending_start'), ('pending_stop', 'pending_stop')], default='offline', max_length=32)),
                ('access_password', models.CharField(blank=True, default='', max_length=255)),
                ('last_activity', models.FloatField(blank=True, null=True)),
                ('current_server', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='current_users', to='backend.serveroption')),
            ],
            options={'ordering': ['username']},
        ),
        migrations.CreateModel(
            name='UserServer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('server', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_servers', to='backend.serveroption')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_servers', to='backend.user')),
            ],
            options={'unique_together': {('user', 'server')}},
        ),
        migrations.AddField(
            model_name='user',
            name='allowed_servers',
            field=models.ManyToManyField(related_name='users', through='backend.UserServer', to='backend.serveroption'),
        ),
    ]
