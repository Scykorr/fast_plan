"""CRM custom field definition + entity value APIs."""

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from crm.custom_fields import (
    list_definitions,
    set_values,
    validate_definition_options,
    values_map,
)
from crm.models import CrmCustomFieldDefinition
from crm.serializers import CrmCustomFieldDefinitionSerializer
from workspaces.mixins import IsWorkspaceEditorOrReadOnly, WorkspaceMixin


class CrmCustomFieldDefinitionListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        target = request.query_params.get("target")
        active = request.query_params.get("active")
        active_only = active != "0"
        qs = list_definitions(
            self.get_workspace(), target=target or None, active_only=active_only
        )
        return Response(CrmCustomFieldDefinitionSerializer(qs, many=True).data)

    def post(self, request):
        target = (request.data.get("target") or "").strip()
        key = (request.data.get("key") or "").strip().lower().replace(" ", "_")
        label = (request.data.get("label") or "").strip()
        field_type = (request.data.get("field_type") or "text").strip()
        if target not in dict(CrmCustomFieldDefinition.Target.choices):
            raise ValidationError({"target": "Invalid target."})
        if not key:
            raise ValidationError({"key": "Required."})
        if not label:
            raise ValidationError({"label": "Required."})
        if field_type not in dict(CrmCustomFieldDefinition.FieldType.choices):
            raise ValidationError({"field_type": "Invalid type."})
        options = validate_definition_options(field_type, request.data.get("options") or [])
        row = CrmCustomFieldDefinition.objects.create(
            workspace=self.get_workspace(),
            target=target,
            key=key,
            label=label,
            field_type=field_type,
            options=options,
            required=bool(request.data.get("required")),
            position=int(request.data.get("position") or 0),
            is_active=True,
        )
        return Response(
            CrmCustomFieldDefinitionSerializer(row).data,
            status=status.HTTP_201_CREATED,
        )


class CrmCustomFieldDefinitionDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def patch(self, request, field_id):
        row = get_object_or_404(
            CrmCustomFieldDefinition,
            pk=field_id,
            workspace=self.get_workspace(),
        )
        if "label" in request.data:
            row.label = str(request.data.get("label") or "").strip() or row.label
        if "field_type" in request.data:
            ft = str(request.data.get("field_type") or "").strip()
            if ft not in dict(CrmCustomFieldDefinition.FieldType.choices):
                raise ValidationError({"field_type": "Invalid type."})
            row.field_type = ft
        if "options" in request.data:
            row.options = validate_definition_options(
                row.field_type, request.data.get("options") or []
            )
        if "required" in request.data:
            row.required = bool(request.data.get("required"))
        if "position" in request.data:
            row.position = int(request.data.get("position") or 0)
        if "is_active" in request.data:
            row.is_active = bool(request.data.get("is_active"))
        row.save()
        return Response(CrmCustomFieldDefinitionSerializer(row).data)

    def delete(self, request, field_id):
        row = get_object_or_404(
            CrmCustomFieldDefinition,
            pk=field_id,
            workspace=self.get_workspace(),
        )
        row.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CrmEntityCustomFieldsView(WorkspaceMixin, APIView):
    """GET/PUT values for a CRM entity: /api/crm/<target>/<id>/custom-fields/"""

    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request, target, entity_id):
        if target not in dict(CrmCustomFieldDefinition.Target.choices):
            raise ValidationError({"target": "Invalid."})
        return Response(
            {
                "target": target,
                "entity_id": entity_id,
                "values": values_map(self.get_workspace(), target, entity_id),
                "definitions": CrmCustomFieldDefinitionSerializer(
                    list_definitions(self.get_workspace(), target), many=True
                ).data,
            }
        )

    def put(self, request, target, entity_id):
        if target not in dict(CrmCustomFieldDefinition.Target.choices):
            raise ValidationError({"target": "Invalid."})
        payload = request.data.get("values")
        if payload is None and isinstance(request.data, dict):
            payload = {
                k: v
                for k, v in request.data.items()
                if k not in ("values", "target", "entity_id")
            }
        if not isinstance(payload, dict):
            raise ValidationError({"values": "Object required."})
        values = set_values(self.get_workspace(), target, entity_id, payload)
        return Response({"target": target, "entity_id": entity_id, "values": values})
