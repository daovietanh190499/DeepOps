# Copyright (C) 2022 Intel Corporation
# Copyright (C) 2023 CVAT.ai Corporation
#
# SPDX-License-Identifier: MIT

from typing import Any, Dict, Iterator, Optional
from django.utils.translation import gettext_lazy as _
from django.utils.encoding import force_str
from rest_framework import filters
from rest_framework.compat import coreapi, coreschema

DEFAULT_LOOKUP_MAP_ATTR = 'lookup_fields'

def get_lookup_fields(view, fields: Optional[Iterator[str]] = None) -> Dict[str, str]:
    lookup_overrides = getattr(view, DEFAULT_LOOKUP_MAP_ATTR, None) or {}
    lookup_fields = {
        field: lookup_overrides.get(field, field)
        for field in fields
    }
    return lookup_fields

class OrderingFilter(filters.OrderingFilter):
    ordering_param = 'sort'

    def get_ordering(self, request, queryset, view):
        ordering = []
        lookup_fields = self._get_lookup_fields(request, queryset, view)
        for term in super().get_ordering(request, queryset, view):
            flag = ''
            if term.startswith("-"):
                flag = '-'
                term = term[1:]
            ordering.append(flag + lookup_fields[term])

        return ordering

    def _get_lookup_fields(self, request, queryset, view):
        ordering_fields = self.get_valid_fields(queryset, view, {'request': request})
        ordering_fields = [v[0] for v in ordering_fields]
        return get_lookup_fields(view, ordering_fields)

    def get_schema_fields(self, view):
        assert coreapi is not None, 'coreapi must be installed to use `get_schema_fields()`'
        assert coreschema is not None, 'coreschema must be installed to use `get_schema_fields()`'

        ordering_fields = getattr(view, 'ordering_fields', [])
        full_description = self.ordering_description + \
            f' Available ordering_fields: {ordering_fields}'

        return [
            coreapi.Field(
                name=self.ordering_param,
                required=False,
                location='query',
                schema=coreschema.String(
                    title=force_str(self.ordering_title),
                    description=force_str(full_description)
                )
            )
        ] if ordering_fields else []

    def get_schema_operation_parameters(self, view):
        ordering_fields = getattr(view, 'ordering_fields', [])
        full_description = self.ordering_description + \
            f' Available ordering_fields: {ordering_fields}'

        return [{
            'name': self.ordering_param,
            'required': False,
            'in': 'query',
            'description': force_str(full_description),
            'schema': {
                'type': 'string',
            },
        }] if ordering_fields else []