from django.db import migrations, models


def set_template_docker_defaults(apps, schema_editor):
    ServerPlanTemplate = apps.get_model('backend', 'ServerPlanTemplate')
    ServerPlanTemplate.objects.update(
        docker_repository='codercom/code-server',
        docker_tag='4.89.0-ubuntu',
        exposed_ports=[8080],
    )


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0012_dockerimage_tags'),
    ]

    operations = [
        migrations.AddField(
            model_name='serverplantemplate',
            name='docker_repository',
            field=models.CharField(blank=True, default='', max_length=512),
        ),
        migrations.AddField(
            model_name='serverplantemplate',
            name='docker_tag',
            field=models.CharField(blank=True, default='', max_length=128),
        ),
        migrations.AddField(
            model_name='serverplantemplate',
            name='exposed_ports',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.RunPython(set_template_docker_defaults, migrations.RunPython.noop),
    ]
