from django.db import migrations


def migrate_password_prefix_templates(apps, schema_editor):
    ServerPlanTemplate = apps.get_model('backend', 'ServerPlanTemplate')
    for template in ServerPlanTemplate.objects.all():
        env = dict(template.env_defaults or {})
        prefix = env.pop('PASSWORD_PREFIX', None)
        if prefix is not None and 'PASSWORD' not in env:
            env['PASSWORD'] = f'{prefix}<<rdstring:6>>'
        if env != (template.env_defaults or {}):
            template.env_defaults = env
            template.save(update_fields=['env_defaults'])


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0014_serverplantemplate_command'),
    ]

    operations = [
        migrations.RunPython(migrate_password_prefix_templates, migrations.RunPython.noop),
    ]
