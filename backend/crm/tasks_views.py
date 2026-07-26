from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from crm.models import DealTask, Lead, LeadTask
from crm.serializers import LeadTaskSerializer, LeadTaskWriteSerializer
from crm.task_helpers import (
    apply_task_fields,
    board_item_from_deal_task,
    board_item_from_lead_task,
    normalize_checklist,
)
from workspaces.mixins import IsWorkspaceEditorOrReadOnly, WorkspaceMixin
from workspaces.models import WorkspaceMember


def _resolve_assignee(workspace, user_id):
    if user_id is None:
        return None
    member = WorkspaceMember.objects.filter(
        workspace=workspace, user_id=user_id
    ).first()
    if member is None:
        raise ValidationError({"assignee_id": "User is not a workspace member."})
    return member.user


class CrmTaskBoardView(WorkspaceMixin, APIView):
    """Unified Deal + Lead task board for Kanban."""

    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        workspace = self.get_workspace()
        status_filter = (request.query_params.get("board_status") or "").strip()
        kind = (request.query_params.get("kind") or "").strip()
        include_done = request.query_params.get("include_done") in (
            "1",
            "true",
            "yes",
        )

        items: list[dict] = []
        if kind in ("", "deal"):
            deal_qs = DealTask.objects.filter(
                deal__workspace=workspace
            ).select_related("deal", "assignee")
            if status_filter:
                deal_qs = deal_qs.filter(board_status=status_filter)
            elif not include_done:
                deal_qs = deal_qs.exclude(board_status=DealTask.BoardStatus.DONE)
            items.extend(board_item_from_deal_task(t) for t in deal_qs)

        if kind in ("", "lead"):
            lead_qs = LeadTask.objects.filter(
                lead__workspace=workspace
            ).select_related("lead", "assignee")
            if status_filter:
                lead_qs = lead_qs.filter(board_status=status_filter)
            elif not include_done:
                lead_qs = lead_qs.exclude(board_status=LeadTask.BoardStatus.DONE)
            items.extend(board_item_from_lead_task(t) for t in lead_qs)

        priority_rank = {"urgent": 0, "high": 1, "normal": 2, "low": 3}
        items.sort(
            key=lambda row: (
                {"todo": 0, "doing": 1, "done": 2}.get(row["board_status"], 9),
                priority_rank.get(row["priority"], 9),
                row["due_date"] or "9999-99-99",
                row["id"],
            )
        )
        return Response({"results": items, "count": len(items)})


class CrmTaskBoardMoveView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def patch(self, request, kind, task_id):
        workspace = self.get_workspace()
        board_status = request.data.get("board_status")
        if board_status not in {
            DealTask.BoardStatus.TODO,
            DealTask.BoardStatus.DOING,
            DealTask.BoardStatus.DONE,
        }:
            raise ValidationError({"board_status": "Invalid board status."})

        if kind == "deal":
            task = get_object_or_404(
                DealTask.objects.filter(deal__workspace=workspace).select_related(
                    "deal", "assignee"
                ),
                pk=task_id,
            )
            apply_task_fields(
                task, {"board_status": board_status}, request_data={"board_status": board_status}
            )
            return Response(board_item_from_deal_task(task))

        if kind == "lead":
            task = get_object_or_404(
                LeadTask.objects.filter(lead__workspace=workspace).select_related(
                    "lead", "assignee"
                ),
                pk=task_id,
            )
            apply_task_fields(
                task, {"board_status": board_status}, request_data={"board_status": board_status}
            )
            return Response(board_item_from_lead_task(task))

        raise ValidationError({"kind": "Must be deal or lead."})


class LeadTaskListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_lead(self, lead_id):
        return get_object_or_404(
            Lead.objects.filter(workspace=self.get_workspace()),
            pk=lead_id,
        )

    def get(self, request, lead_id):
        lead = self.get_lead(lead_id)
        tasks = lead.tasks.select_related("assignee")
        return Response(LeadTaskSerializer(tasks, many=True).data)

    def post(self, request, lead_id):
        lead = self.get_lead(lead_id)
        serializer = LeadTaskWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if not data.get("title"):
            raise ValidationError({"title": "This field is required."})
        assignee = None
        if "assignee_id" in data or "assignee_id" in request.data:
            assignee = _resolve_assignee(
                self.get_workspace(), request.data.get("assignee_id", data.get("assignee_id"))
            )
        is_done = data.get("is_done", False)
        task = LeadTask.objects.create(
            lead=lead,
            title=data["title"],
            due_date=data.get("due_date"),
            is_done=is_done,
            priority=data.get("priority", LeadTask.Priority.NORMAL),
            board_status=(
                LeadTask.BoardStatus.DONE
                if is_done
                else data.get("board_status", LeadTask.BoardStatus.TODO)
            ),
            checklist=normalize_checklist(request.data.get("checklist", data.get("checklist"))),
            repeat=data.get("repeat", LeadTask.Repeat.NONE),
            assignee=assignee,
            remind_before_days=data.get("remind_before_days", 1),
            notes=data.get("notes", ""),
        )
        return Response(
            LeadTaskSerializer(task).data, status=status.HTTP_201_CREATED
        )


class LeadTaskDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_task(self, lead_id, task_id):
        return get_object_or_404(
            LeadTask.objects.filter(
                lead_id=lead_id, lead__workspace=self.get_workspace()
            ),
            pk=task_id,
        )

    def patch(self, request, lead_id, task_id):
        task = self.get_task(lead_id, task_id)
        serializer = LeadTaskWriteSerializer(
            data={**request.data, "title": request.data.get("title", task.title)}
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if "assignee_id" in request.data:
            task.assignee = _resolve_assignee(
                self.get_workspace(), data.get("assignee_id")
            )
        apply_task_fields(task, data, request_data=request.data)
        return Response(LeadTaskSerializer(task).data)

    def delete(self, request, lead_id, task_id):
        self.get_task(lead_id, task_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
