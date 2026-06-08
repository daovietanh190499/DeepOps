from django.db import migrations, models


def copy_default_tag_to_tags(apps, schema_editor):
    DockerImage = apps.get_model('backend', 'DockerImage')
    for img in DockerImage.objects.all():
        tag = (img.default_tag or 'latest').strip()
        img.tags = [tag] if tag else ['latest']
        img.save(update_fields=['tags'])


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0011_privileged_and_shared_drives'),
    ]

    operations = [
        migrations.AddField(
            model_name='dockerimage',
            name='tags',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Selectable image tags; default_tag should be included',
            ),
        ),
        migrations.RunPython(copy_default_tag_to_tags, migrations.RunPython.noop),
    ]
