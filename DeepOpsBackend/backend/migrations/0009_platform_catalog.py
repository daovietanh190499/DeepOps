from django.db import migrations, models


def seed_platform_catalog(apps, schema_editor):
    PlatformEquipmentOption = apps.get_model('backend', 'PlatformEquipmentOption')
    ServerPlanTemplate = apps.get_model('backend', 'ServerPlanTemplate')

    cpu = [2, 4, 8, 16, 32]
    for i, value in enumerate(cpu):
        PlatformEquipmentOption.objects.get_or_create(
            category='cpu',
            value=str(value),
            defaults={'sort_order': i, 'is_active': True},
        )

    ram = ['2G', '4G', '8G', '16G', '32G', '64G']
    for i, value in enumerate(ram):
        PlatformEquipmentOption.objects.get_or_create(
            category='ram',
            value=value,
            defaults={'sort_order': i, 'is_active': True},
        )

    gpu_options = [
        ('none', 0),
        ('mig-2g.10gb', 10),
        ('mig-3g.20gb', 20),
        ('gpu', 40),
        ('gpu:2', 80),
    ]
    for i, (value, vram) in enumerate(gpu_options):
        PlatformEquipmentOption.objects.get_or_create(
            category='gpu',
            value=value,
            defaults={'sort_order': i, 'vram_g': vram, 'is_active': True},
        )

    drive_sizes = ['20Gi', '50Gi', '100Gi', '200Gi', '500Gi', '1Ti']
    for i, value in enumerate(drive_sizes):
        PlatformEquipmentOption.objects.get_or_create(
            category='drive_size',
            value=value,
            defaults={'sort_order': i, 'is_active': True},
        )

    templates = [
        {
            'name': 'Lollipop',
            'image': 'lollipop.png',
            'cpu': 2,
            'ram': '4G',
            'gpu': 'none',
            'env_defaults': {'PASSWORD_PREFIX': 'lollipop-', 'PWA_APPNAME': 'Lollipop'},
            'sort_order': 0,
        },
        {
            'name': 'Oreo',
            'image': 'oreo.png',
            'cpu': 4,
            'ram': '8G',
            'gpu': 'mig-2g.10gb',
            'env_defaults': {'PASSWORD_PREFIX': 'oreo-', 'PWA_APPNAME': 'Oreo'},
            'sort_order': 1,
        },
        {
            'name': 'Popeyes',
            'image': 'popeyes.png',
            'cpu': 8,
            'ram': '16G',
            'gpu': 'mig-3g.20gb',
            'env_defaults': {'PASSWORD_PREFIX': 'popeyes-', 'PWA_APPNAME': 'Popeyes'},
            'sort_order': 2,
        },
        {
            'name': 'Pizza',
            'image': 'pizza.png',
            'cpu': 8,
            'ram': '32G',
            'gpu': 'gpu',
            'env_defaults': {'PASSWORD_PREFIX': 'pizza-', 'PWA_APPNAME': 'Pizza'},
            'sort_order': 3,
        },
        {
            'name': 'Spagetti',
            'image': 'spagetti.png',
            'cpu': 16,
            'ram': '64G',
            'gpu': 'gpu:2',
            'env_defaults': {'PASSWORD_PREFIX': 'spagetti-', 'PWA_APPNAME': 'Spagetti'},
            'sort_order': 4,
        },
    ]
    for item in templates:
        ServerPlanTemplate.objects.get_or_create(
            name=item['name'],
            defaults=item,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0008_workspacedrivemount'),
    ]

    operations = [
        migrations.CreateModel(
            name='PlatformEquipmentOption',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.CharField(choices=[('cpu', 'cpu'), ('ram', 'ram'), ('gpu', 'gpu'), ('drive_size', 'drive_size')], max_length=32)),
                ('value', models.CharField(max_length=64)),
                ('vram_g', models.PositiveIntegerField(default=0, help_text='GPU VRAM in GB (gpu category only)')),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['category', 'sort_order', 'value'],
                'unique_together': {('category', 'value')},
            },
        ),
        migrations.CreateModel(
            name='ServerPlanTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=128, unique=True)),
                ('image', models.CharField(default='logo.png', max_length=255)),
                ('cpu', models.PositiveIntegerField(default=2)),
                ('ram', models.CharField(default='4G', max_length=64)),
                ('gpu', models.CharField(default='none', max_length=64)),
                ('env_defaults', models.JSONField(blank=True, default=dict)),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['sort_order', 'name'],
            },
        ),
        migrations.RunPython(seed_platform_catalog, migrations.RunPython.noop),
    ]
