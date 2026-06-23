from django.db import migrations


def _workspace_columns(schema_editor):
    model = schema_editor.connection.introspection
    table = 'backend_workspace'
    with schema_editor.connection.cursor() as cursor:
        return {
            col.name
            for col in model.get_table_description(cursor, table)
        }


def _drop_workspace_column(schema_editor, column: str) -> None:
    table = 'backend_workspace'
    connection = schema_editor.connection
    columns = _workspace_columns(schema_editor)
    if column not in columns:
        return
    if connection.vendor == 'sqlite':
        with connection.cursor() as cursor:
            cursor.execute(
                f'ALTER TABLE {schema_editor.quote_name(table)} '
                f'DROP COLUMN {schema_editor.quote_name(column)}'
            )
        return
    schema_editor.execute(
        schema_editor.sql_delete_column
        % {
            'table': schema_editor.quote_name(table),
            'column': schema_editor.quote_name(column),
        }
    )


def drop_legacy_routing_artifacts(apps, schema_editor):
    """Remove path-routing experiment columns/tables left on older databases."""
    connection = schema_editor.connection
    for column in ('routing_mode', 'custom_ingress_path'):
        _drop_workspace_column(schema_editor, column)

    with connection.cursor() as cursor:
        tables = set(connection.introspection.table_names(cursor))
    if 'backend_hubsettings' in tables:
        schema_editor.execute(
            schema_editor.sql_delete_table
            % {'table': schema_editor.quote_name('backend_hubsettings')}
        )


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0030_workspace_custom_ingress_path'),
    ]

    operations = [
        migrations.RunPython(
            drop_legacy_routing_artifacts,
            migrations.RunPython.noop,
        ),
    ]
