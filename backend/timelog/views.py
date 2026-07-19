from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from projects.models import WBSNode
from timelog.models import TimeEntry
from timelog.serializers import TimeEntrySerializer, TimeEntryWriteSerializer
from workspaces.mixins import IsWorkspaceEditorOrReadOnly, WorkspaceMixin
from workspaces.models import WorkspaceMember
from workspaces.services import has_min_role


class TimeEntryListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        workspace = self.get_workspace()
        entries = TimeEntry.objects.filter(workspace=workspace).select_related(
            "user", "wbs_node"
        )
        wbs_id = request.query_params.get("wbs_node")
        if wbs_id:
            entries = entries.filter(wbs_node_id=wbs_id)
        user_id = request.query_params.get("user")
        if user_id:
            entries = entries.filter(user_id=user_id)
        return Response(TimeEntrySerializer(entries, many=True).data)

    def post(self, request):
        workspace = self.get_workspace()
        serializer = TimeEntryWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        node = get_object_or_404(
            WBSNode.objects.filter(project__workspace=workspace),
            pk=data["wbs_node"].id,
        )
        entry = TimeEntry.objects.create(
            workspace=workspace,
            user=request.user,
            wbs_node=node,
            hours=data["hours"],
            work_date=data["work_date"],
            notes=data.get("notes", ""),
        )
        return Response(TimeEntrySerializer(entry).data, status=status.HTTP_201_CREATED)


class TimeEntryDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_entry(self, entry_id):
        return get_object_or_404(
            TimeEntry.objects.filter(workspace=self.get_workspace()),
            pk=entry_id,
        )

    def _check_owner_or_author(self, entry):
        workspace = self.get_workspace()
        if entry.user_id != self.request.user.id and not has_min_role(
            workspace, self.request.user, WorkspaceMember.Role.OWNER
        ):
            raise ValidationError("Only the author or workspace owner can modify this entry.")

    def patch(self, request, entry_id):
        entry = self.get_entry(entry_id)
        self._check_owner_or_author(entry)
        serializer = TimeEntryWriteSerializer(entry, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if "wbs_node" in data:
            node = get_object_or_404(
                WBSNode.objects.filter(project__workspace=self.get_workspace()),
                pk=data["wbs_node"].id,
            )
            entry.wbs_node = node
        for field in ("hours", "work_date", "notes"):
            if field in data:
                setattr(entry, field, data[field])
        entry.save()
        return Response(TimeEntrySerializer(entry).data)

    def delete(self, request, entry_id):
        entry = self.get_entry(entry_id)
        self._check_owner_or_author(entry)
        entry.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
