from django.db import migrations


def drop_custom_ingress_path_column(apps, schema_editor):
    """Remove legacy column left by an older routing experiment."""
    model = apps.get_model('backend', 'Workspace')
    table = model._meta.db_table
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        columns = {
            col.name
            for col in connection.introspection.get_table_description(cursor, table)
        }
    if 'custom_ingress_path' not in columns:
        return

    if connection.vendor == 'sqlite':
        with connection.cursor() as cursor:
            cursor.execute(
                f'ALTER TABLE {schema_editor.quote_name(table)} '
                f'DROP COLUMN {schema_editor.quote_name("custom_ingress_path")}'
            )
        return

    schema_editor.execute(
        schema_editor.sql_delete_column
        % {
            'table': schema_editor.quote_name(table),
            'column': schema_editor.quote_name('custom_ingress_path'),
        }
    )


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0029_delete_workspacesshkey'),
    ]

    operations = [
        migrations.RunPython(
            drop_custom_ingress_path_column,
            migrations.RunPython.noop,
        ),
    ]
