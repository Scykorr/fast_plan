"""OBS (Organizational Breakdown Structure) API — org units + job roles."""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from workspaces.mixins import IsWorkspaceEditorOrReadOnly, WorkspaceMixin
from workspaces.models import ObsRole, OrgUnit
from workspaces.serializers import ObsRoleSerializer, OrgUnitSerializer


def _org_unit_tree(units: list[OrgUnit]) -> list[dict]:
    by_parent: dict[int | None, list[OrgUnit]] = {}
    for unit in units:
        by_parent.setdefault(unit.parent_id, []).append(unit)

    def serialize(unit: OrgUnit) -> dict:
        return {
            "id": unit.id,
            "code": unit.code,
            "name": unit.name,
            "position": unit.position,
            "parent_id": unit.parent_id,
            "children": [serialize(child) for child in by_parent.get(unit.id, [])],
        }

    return [serialize(root) for root in by_parent.get(None, [])]


class OrgUnitListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        workspace = self.get_workspace()
        units = list(
            OrgUnit.objects.filter(workspace=workspace).order_by("position", "id")
        )
        flat = request.query_params.get("flat") in ("1", "true", "yes")
        if flat:
            return Response(OrgUnitSerializer(units, many=True).data)
        return Response(_org_unit_tree(units))

    def post(self, request):
        workspace = self.get_workspace()
        name = str(request.data.get("name") or "").strip()
        if not name:
            raise ValidationError({"name": "Required."})
        parent_id = request.data.get("parent_id")
        parent = None
        if parent_id not in (None, ""):
            parent = get_object_or_404(
                OrgUnit.objects.filter(workspace=workspace), pk=parent_id
            )
        siblings = OrgUnit.objects.filter(workspace=workspace, parent=parent)
        position = request.data.get("position")
        if position is None:
            position = siblings.count()
        unit = OrgUnit.objects.create(
            workspace=workspace,
            parent=parent,
            name=name,
            code=str(request.data.get("code") or "").strip()[:50],
            position=int(position),
        )
        return Response(OrgUnitSerializer(unit).data, status=status.HTTP_201_CREATED)


class OrgUnitDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_object(self, unit_id):
        return get_object_or_404(
            OrgUnit.objects.filter(workspace=self.get_workspace()), pk=unit_id
        )

    def patch(self, request, unit_id):
        unit = self.get_object(unit_id)
        if "name" in request.data:
            name = str(request.data.get("name") or "").strip()
            if not name:
                raise ValidationError({"name": "Required."})
            unit.name = name
        if "code" in request.data:
            unit.code = str(request.data.get("code") or "").strip()[:50]
        if "position" in request.data and request.data.get("position") is not None:
            unit.position = int(request.data["position"])
        if "parent_id" in request.data:
            parent_id = request.data.get("parent_id")
            if parent_id in (None, ""):
                unit.parent = None
            else:
                parent = get_object_or_404(
                    OrgUnit.objects.filter(workspace=unit.workspace),
                    pk=parent_id,
                )
                if parent.id == unit.id:
                    raise ValidationError({"parent_id": "Cannot set parent to self."})
                # Prevent cycles
                cursor = parent
                while cursor is not None:
                    if cursor.id == unit.id:
                        raise ValidationError(
                            {"parent_id": "Cannot move unit under its descendant."}
                        )
                    cursor = cursor.parent
                unit.parent = parent
        unit.save()
        return Response(OrgUnitSerializer(unit).data)

    def delete(self, request, unit_id):
        unit = self.get_object(unit_id)
        unit.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ObsRoleListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        roles = ObsRole.objects.filter(workspace=self.get_workspace()).order_by(
            "position", "name", "id"
        )
        return Response(ObsRoleSerializer(roles, many=True).data)

    def post(self, request):
        workspace = self.get_workspace()
        name = str(request.data.get("name") or "").strip()
        if not name:
            raise ValidationError({"name": "Required."})
        if ObsRole.objects.filter(workspace=workspace, name__iexact=name).exists():
            raise ValidationError({"name": "Role name must be unique."})
        position = request.data.get("position")
        if position is None:
            position = ObsRole.objects.filter(workspace=workspace).count()
        role = ObsRole.objects.create(
            workspace=workspace,
            name=name,
            code=str(request.data.get("code") or "").strip()[:50],
            position=int(position),
        )
        return Response(ObsRoleSerializer(role).data, status=status.HTTP_201_CREATED)


class ObsRoleDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_object(self, role_id):
        return get_object_or_404(
            ObsRole.objects.filter(workspace=self.get_workspace()), pk=role_id
        )

    def patch(self, request, role_id):
        role = self.get_object(role_id)
        if "name" in request.data:
            name = str(request.data.get("name") or "").strip()
            if not name:
                raise ValidationError({"name": "Required."})
            clash = (
                ObsRole.objects.filter(workspace=role.workspace, name__iexact=name)
                .exclude(pk=role.pk)
                .exists()
            )
            if clash:
                raise ValidationError({"name": "Role name must be unique."})
            role.name = name
        if "code" in request.data:
            role.code = str(request.data.get("code") or "").strip()[:50]
        if "position" in request.data and request.data.get("position") is not None:
            role.position = int(request.data["position"])
        role.save()
        return Response(ObsRoleSerializer(role).data)

    def delete(self, request, role_id):
        role = self.get_object(role_id)
        role.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
