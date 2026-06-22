"""Workspace DB helpers."""

from __future__ import annotations

import uuid

from django.db import connection


def purge_legacy_workspace_rows(workspace_id: uuid.UUID) -> None:
    """Remove orphaned rows from legacy tables not wired into Django CASCADE."""
    tables = set(connection.introspection.table_names())
    if 'backend_workspacesshkey' not in tables:
        return
    with connection.cursor() as cursor:
        cursor.execute(
            'DELETE FROM backend_workspacesshkey WHERE workspace_id = %s',
            [str(workspace_id)],
        )
