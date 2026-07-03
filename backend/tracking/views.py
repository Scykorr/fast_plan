from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from tracking.models import CustomField, CustomFieldEnumeration, IssueStatus, Tracker
from tracking.serializers import (
    CustomFieldEnumerationSerializer,
    CustomFieldSerializer,
    IssueStatusSerializer,
    TrackerSerializer,
)
from tracking.services import seed_workspace_tracking, serialize_field_definition
from workspaces.services import get_user_workspace


class WorkspaceMixin:
    def get_workspace(self):
        workspace = get_user_workspace(self.request.user)
        if workspace is None:
            raise NotFound("Workspace not found.")
        return workspace


class TrackingMetadataView(WorkspaceMixin, APIView):
    def get(self, request):
        workspace = self.get_workspace()
        seed_workspace_tracking(workspace)
        trackers = Tracker.objects.filter(workspace=workspace)
        statuses = IssueStatus.objects.filter(workspace=workspace)
        fields = CustomField.objects.filter(workspace=workspace).prefetch_related(
            "enumerations", "trackers"
        )
        return Response(
            {
                "trackers": TrackerSerializer(trackers, many=True).data,
                "statuses": IssueStatusSerializer(statuses, many=True).data,
                "custom_fields": [
                    serialize_field_definition(field) for field in fields
                ],
            }
        )


class TrackerListCreateView(WorkspaceMixin, APIView):
    def get(self, request):
        workspace = self.get_workspace()
        trackers = Tracker.objects.filter(workspace=workspace)
        return Response(TrackerSerializer(trackers, many=True).data)

    def post(self, request):
        workspace = self.get_workspace()
        serializer = TrackerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tracker = Tracker.objects.create(
            workspace=workspace,
            name=serializer.validated_data["name"],
            description=serializer.validated_data.get("description", ""),
            target=serializer.validated_data.get("target", Tracker.Target.ISSUE),
            position=serializer.validated_data.get(
                "position", Tracker.objects.filter(workspace=workspace).count()
            ),
            is_default=serializer.validated_data.get("is_default", False),
        )
        return Response(TrackerSerializer(tracker).data, status=status.HTTP_201_CREATED)


class TrackerDetailView(WorkspaceMixin, APIView):
    def get_tracker(self, tracker_id):
        return get_object_or_404(
            Tracker.objects.filter(workspace=self.get_workspace()),
            pk=tracker_id,
        )

    def patch(self, request, tracker_id):
        tracker = self.get_tracker(tracker_id)
        serializer = TrackerSerializer(tracker, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(TrackerSerializer(tracker).data)

    def delete(self, request, tracker_id):
        tracker = self.get_tracker(tracker_id)
        tracker.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class IssueStatusListCreateView(WorkspaceMixin, APIView):
    def get(self, request):
        workspace = self.get_workspace()
        statuses = IssueStatus.objects.filter(workspace=workspace)
        return Response(IssueStatusSerializer(statuses, many=True).data)

    def post(self, request):
        workspace = self.get_workspace()
        serializer = IssueStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        status_obj = IssueStatus.objects.create(
            workspace=workspace,
            **serializer.validated_data,
        )
        return Response(
            IssueStatusSerializer(status_obj).data,
            status=status.HTTP_201_CREATED,
        )


class IssueStatusDetailView(WorkspaceMixin, APIView):
    def get_status(self, status_id):
        return get_object_or_404(
            IssueStatus.objects.filter(workspace=self.get_workspace()),
            pk=status_id,
        )

    def patch(self, request, status_id):
        status_obj = self.get_status(status_id)
        serializer = IssueStatusSerializer(status_obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(IssueStatusSerializer(status_obj).data)

    def delete(self, request, status_id):
        status_obj = self.get_status(status_id)
        status_obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CustomFieldListCreateView(WorkspaceMixin, APIView):
    def get(self, request):
        workspace = self.get_workspace()
        fields = CustomField.objects.filter(workspace=workspace).prefetch_related(
            "enumerations", "trackers"
        )
        return Response(
            [serialize_field_definition(field) for field in fields]
        )

    def post(self, request):
        workspace = self.get_workspace()
        serializer = CustomFieldSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        field = serializer.save(workspace=workspace)
        return Response(
            serialize_field_definition(field),
            status=status.HTTP_201_CREATED,
        )


class CustomFieldDetailView(WorkspaceMixin, APIView):
    def get_field(self, field_id):
        return get_object_or_404(
            CustomField.objects.filter(workspace=self.get_workspace()).prefetch_related(
                "enumerations", "trackers"
            ),
            pk=field_id,
        )

    def patch(self, request, field_id):
        field = self.get_field(field_id)
        serializer = CustomFieldSerializer(field, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        field = serializer.save()
        return Response(serialize_field_definition(field))

    def delete(self, request, field_id):
        field = self.get_field(field_id)
        field.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CustomFieldEnumerationListCreateView(WorkspaceMixin, APIView):
    def get_field(self, field_id):
        return get_object_or_404(
            CustomField.objects.filter(workspace=self.get_workspace()),
            pk=field_id,
        )

    def post(self, request, field_id):
        field = self.get_field(field_id)
        serializer = CustomFieldEnumerationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = CustomFieldEnumeration.objects.create(
            custom_field=field,
            name=serializer.validated_data["name"],
            position=serializer.validated_data.get(
                "position", field.enumerations.count()
            ),
            is_active=serializer.validated_data.get("is_active", True),
        )
        return Response(
            CustomFieldEnumerationSerializer(item).data,
            status=status.HTTP_201_CREATED,
        )


class CustomFieldEnumerationDetailView(WorkspaceMixin, APIView):
    def get_item(self, item_id):
        return get_object_or_404(
            CustomFieldEnumeration.objects.filter(
                custom_field__workspace=self.get_workspace()
            ),
            pk=item_id,
        )

    def patch(self, request, item_id):
        item = self.get_item(item_id)
        serializer = CustomFieldEnumerationSerializer(
            item, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(CustomFieldEnumerationSerializer(item).data)

    def delete(self, request, item_id):
        item = self.get_item(item_id)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
