from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0022_dockerimage_creator_acceptance'),
    ]

    operations = [
        migrations.AddField(
            model_name='resourcegroup',
            name='max_images',
            field=models.PositiveIntegerField(
                default=0,
                help_text='Max submitted docker images per member; 0 = unlimited',
            ),
        ),
    ]
