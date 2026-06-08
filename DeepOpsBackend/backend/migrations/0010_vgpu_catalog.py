from django.db import migrations


def migrate_gpu_catalog(apps, schema_editor):
    PlatformEquipmentOption = apps.get_model('backend', 'PlatformEquipmentOption')
    ServerPlanTemplate = apps.get_model('backend', 'ServerPlanTemplate')

    legacy_gpu = ['mig-2g.10gb', 'mig-3g.20gb', 'gpu', 'gpu:2']
    PlatformEquipmentOption.objects.filter(category='gpu', value__in=legacy_gpu).update(is_active=False)

    gpu_options = [
        ('none', 0),
        ('1:1024', 1),
        ('1:10240', 10),
        ('1:40960', 40),
        ('2:20480', 40),
    ]
    for i, (value, vram) in enumerate(gpu_options):
        PlatformEquipmentOption.objects.update_or_create(
            category='gpu',
            value=value,
            defaults={'sort_order': i, 'vram_g': vram, 'is_active': True},
        )

    template_gpu = {
        'Oreo': '1:10240',
        'Popeyes': '1:20480',
        'Pizza': '1:40960',
        'Spagetti': '2:20480',
    }
    for name, gpu in template_gpu.items():
        ServerPlanTemplate.objects.filter(name=name).update(gpu=gpu)


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0009_platform_catalog'),
    ]

    operations = [
        migrations.RunPython(migrate_gpu_catalog, migrations.RunPython.noop),
    ]
