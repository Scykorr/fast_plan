from django.conf import settings
from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from crm.models import (
    Activity,
    CrmAttachment,
    CrmComment,
    Organization,
    OrganizationTag,
    Person,
    PersonTag,
    ProjectPersonLink,
    Segment,
    Tag,
)
from crm.serializers import (
    ActivitySerializer,
    ActivityWriteSerializer,
    CrmAttachmentSerializer,
    CrmCommentSerializer,
    CrmCommentWriteSerializer,
    OrganizationSerializer,
    OrganizationWriteSerializer,
    PersonSerializer,
    PersonWriteSerializer,
    ProjectPersonLinkSerializer,
    ProjectPersonLinkWriteSerializer,
    SegmentSerializer,
    SegmentWriteSerializer,
    TagAttachSerializer,
    TagSerializer,
    TagWriteSerializer,
)
from crm.services import (
    annotate_last_activity,
    filter_stale,
    resolve_segment_organizations,
    resolve_segment_people,
    sync_project_stakeholders,
    sync_workspace_contacts,
)
from projects.models import Project
from workspaces.mixins import IsWorkspaceEditorOrReadOnly, IsWorkspaceMember, WorkspaceMixin


def _parse_stale_days(request):
    raw = request.query_params.get("stale_days")
    if not raw:
        return None
    try:
        days = int(raw)
    except (TypeError, ValueError):
        raise ValidationError({"stale_days": "Must be an integer."})
    if days < 1:
        raise ValidationError({"stale_days": "Must be >= 1."})
    return days


def _validate_upload(upload):
    if not upload:
        raise ValidationError({"file": "File is required."})
    if upload.size > settings.ATTACHMENT_MAX_BYTES:
        raise ValidationError(
            {
                "file": (
                    f"File exceeds the {settings.ATTACHMENT_MAX_BYTES} bytes limit."
                )
            }
        )


class OrganizationListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_queryset(self):
        qs = (
            Organization.objects.filter(workspace=self.get_workspace())
            .select_related("owner")
            .prefetch_related("tag_links__tag")
            .annotate(
                people_count=Count("memberships", distinct=True),
                projects_count=Count("client_projects", distinct=True),
            )
        )
        qs = annotate_last_activity(qs, person=False)
        return qs.order_by("name", "id")

    def get(self, request):
        q = (request.query_params.get("q") or "").strip()
        tag_id = request.query_params.get("tag_id")
        segment_id = request.query_params.get("segment_id")
        stale_days = _parse_stale_days(request)
        qs = self.get_queryset()
        if q:
            qs = qs.filter(name__icontains=q)
        if tag_id:
            qs = qs.filter(tag_links__tag_id=tag_id)
        if segment_id:
            segment = get_object_or_404(
                Segment.objects.filter(workspace=self.get_workspace()),
                pk=segment_id,
            )
            org_ids = list(resolve_segment_organizations(segment).values_list("id", flat=True))
            qs = qs.filter(id__in=org_ids)
        if stale_days:
            qs = filter_stale(qs, stale_days)
        orgs = list(qs.distinct()[:200])
        for org in orgs:
            org._prefetched_tags = list(org.tag_links.all())
        return Response(OrganizationSerializer(orgs, many=True).data)

    def post(self, request):
        serializer = OrganizationWriteSerializer(
            data=request.data, context={"workspace": self.get_workspace()}
        )
        serializer.is_valid(raise_exception=True)
        org = serializer.save()
        org = self.get_queryset().get(pk=org.pk)
        org._prefetched_tags = list(org.tag_links.all())
        return Response(
            OrganizationSerializer(org).data, status=status.HTTP_201_CREATED
        )


class OrganizationDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_queryset_base(self):
        qs = (
            Organization.objects.filter(workspace=self.get_workspace())
            .select_related("owner")
            .prefetch_related("tag_links__tag")
            .annotate(
                people_count=Count("memberships", distinct=True),
                projects_count=Count("client_projects", distinct=True),
            )
        )
        return annotate_last_activity(qs, person=False)

    def get_object(self, org_id):
        return get_object_or_404(self.get_queryset_base(), pk=org_id)

    def get(self, request, org_id):
        org = self.get_object(org_id)
        org._prefetched_tags = list(org.tag_links.all())
        return Response(OrganizationSerializer(org).data)

    def patch(self, request, org_id):
        org = self.get_object(org_id)
        serializer = OrganizationWriteSerializer(
            org,
            data=request.data,
            partial=True,
            context={"workspace": self.get_workspace()},
        )
        serializer.is_valid(raise_exception=True)
        org = serializer.save()
        org = self.get_queryset_base().get(pk=org.pk)
        org._prefetched_tags = list(org.tag_links.all())
        return Response(OrganizationSerializer(org).data)

    def delete(self, request, org_id):
        self.get_object(org_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PersonListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_queryset(self):
        qs = (
            Person.objects.filter(workspace=self.get_workspace())
            .select_related("owner")
            .annotate(projects_count=Count("project_links", distinct=True))
            .prefetch_related(
                "organization_memberships__organization",
                "tag_links__tag",
            )
        )
        qs = annotate_last_activity(qs)
        return qs.order_by("full_name", "id")

    def get(self, request):
        from django.db.models import Q

        q = (request.query_params.get("q") or "").strip()
        tag_id = request.query_params.get("tag_id")
        segment_id = request.query_params.get("segment_id")
        stale_days = _parse_stale_days(request)
        qs = self.get_queryset()
        if q:
            qs = qs.filter(
                Q(full_name__icontains=q)
                | Q(email__icontains=q)
                | Q(phone__icontains=q)
                | Q(job_title__icontains=q)
                | Q(telegram__icontains=q)
                | Q(whatsapp__icontains=q)
            )
        if tag_id:
            qs = qs.filter(tag_links__tag_id=tag_id)
        if segment_id:
            segment = get_object_or_404(
                Segment.objects.filter(workspace=self.get_workspace()),
                pk=segment_id,
            )
            person_ids = list(resolve_segment_people(segment).values_list("id", flat=True))
            qs = qs.filter(id__in=person_ids)
        if stale_days:
            qs = filter_stale(qs, stale_days)
        people = list(qs.distinct()[:200])
        for person in people:
            person._prefetched_memberships = list(person.organization_memberships.all())
            person._prefetched_tags = list(person.tag_links.all())
        return Response(PersonSerializer(people, many=True).data)

    def post(self, request):
        serializer = PersonWriteSerializer(
            data=request.data, context={"workspace": self.get_workspace()}
        )
        serializer.is_valid(raise_exception=True)
        person = serializer.save()
        person = self.get_queryset().get(pk=person.pk)
        person._prefetched_memberships = list(
            person.organization_memberships.select_related("organization")
        )
        person._prefetched_tags = list(person.tag_links.all())
        return Response(PersonSerializer(person).data, status=status.HTTP_201_CREATED)


class PersonDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_queryset(self):
        qs = (
            Person.objects.filter(workspace=self.get_workspace())
            .select_related("owner")
            .annotate(projects_count=Count("project_links", distinct=True))
            .prefetch_related("organization_memberships__organization", "tag_links__tag")
        )
        return annotate_last_activity(qs)

    def get_object(self, person_id):
        return get_object_or_404(self.get_queryset(), pk=person_id)

    def get(self, request, person_id):
        person = self.get_object(person_id)
        person._prefetched_memberships = list(
            person.organization_memberships.select_related("organization")
        )
        person._prefetched_tags = list(person.tag_links.all())
        return Response(PersonSerializer(person).data)

    def patch(self, request, person_id):
        person = self.get_object(person_id)
        serializer = PersonWriteSerializer(
            person,
            data=request.data,
            partial=True,
            context={"workspace": self.get_workspace()},
        )
        serializer.is_valid(raise_exception=True)
        person = serializer.save()
        person = self.get_object(person.id)
        person._prefetched_memberships = list(
            person.organization_memberships.select_related("organization")
        )
        person._prefetched_tags = list(person.tag_links.all())
        return Response(PersonSerializer(person).data)

    def delete(self, request, person_id):
        self.get_object(person_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ActivityListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        qs = Activity.objects.filter(workspace=self.get_workspace()).select_related(
            "person", "organization", "project", "created_by"
        )
        person_id = request.query_params.get("person_id")
        org_id = request.query_params.get("organization_id")
        project_id = request.query_params.get("project_id")
        if person_id:
            qs = qs.filter(person_id=person_id)
        if org_id:
            qs = qs.filter(organization_id=org_id)
        if project_id:
            qs = qs.filter(project_id=project_id)
        return Response(ActivitySerializer(qs[:100], many=True).data)

    def post(self, request):
        serializer = ActivityWriteSerializer(
            data=request.data,
            context={"workspace": self.get_workspace(), "request": request},
        )
        serializer.is_valid(raise_exception=True)
        activity = serializer.save()
        activity = Activity.objects.select_related(
            "person", "organization", "project", "created_by"
        ).get(pk=activity.pk)
        return Response(
            ActivitySerializer(activity).data, status=status.HTTP_201_CREATED
        )


class ActivityDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_object(self, activity_id):
        return get_object_or_404(
            Activity.objects.filter(workspace=self.get_workspace()),
            pk=activity_id,
        )

    def delete(self, request, activity_id):
        self.get_object(activity_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProjectPeopleView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_project(self, project_id):
        return get_object_or_404(
            Project.objects.filter(workspace=self.get_workspace()),
            pk=project_id,
        )

    def get(self, request, project_id):
        project = self.get_project(project_id)
        links = project.crm_people.select_related("person").all()
        return Response(ProjectPersonLinkSerializer(links, many=True).data)

    def post(self, request, project_id):
        project = self.get_project(project_id)
        serializer = ProjectPersonLinkWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        person = get_object_or_404(
            Person.objects.filter(workspace=self.get_workspace()),
            pk=data["person_id"],
        )
        link, _ = ProjectPersonLink.objects.update_or_create(
            project=project,
            person=person,
            defaults={
                "role_kind": data["role_kind"],
                "role_label": data.get("role_label", ""),
                "interest": data.get("interest", 3),
                "influence": data.get("influence", 3),
                "notes": data.get("notes", ""),
            },
        )
        return Response(
            ProjectPersonLinkSerializer(link).data, status=status.HTTP_201_CREATED
        )


class CrmImportLegacyView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceMember]

    def post(self, request):
        workspace = self.get_workspace()
        contacts = sync_workspace_contacts(workspace)
        stakeholders = 0
        for project in Project.objects.filter(workspace=workspace):
            stakeholders += sync_project_stakeholders(project)
        return Response(
            {
                "imported_contacts": contacts,
                "imported_stakeholders": stakeholders,
                "synced_at": timezone.now().isoformat(),
            }
        )


class TagListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        tags = Tag.objects.filter(workspace=self.get_workspace())
        return Response(TagSerializer(tags, many=True).data)

    def post(self, request):
        serializer = TagWriteSerializer(
            data=request.data, context={"workspace": self.get_workspace()}
        )
        serializer.is_valid(raise_exception=True)
        tag = serializer.save()
        return Response(TagSerializer(tag).data, status=status.HTTP_201_CREATED)


class TagDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_object(self, tag_id):
        return get_object_or_404(
            Tag.objects.filter(workspace=self.get_workspace()),
            pk=tag_id,
        )

    def patch(self, request, tag_id):
        tag = self.get_object(tag_id)
        serializer = TagWriteSerializer(tag, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        tag = serializer.save()
        return Response(TagSerializer(tag).data)

    def delete(self, request, tag_id):
        self.get_object(tag_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PersonTagView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def post(self, request, person_id):
        person = get_object_or_404(
            Person.objects.filter(workspace=self.get_workspace()),
            pk=person_id,
        )
        serializer = TagAttachSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tag = serializer.resolve_tag(self.get_workspace())
        PersonTag.objects.get_or_create(person=person, tag=tag)
        return Response(TagSerializer(tag).data, status=status.HTTP_201_CREATED)

    def delete(self, request, person_id, tag_id):
        person = get_object_or_404(
            Person.objects.filter(workspace=self.get_workspace()),
            pk=person_id,
        )
        deleted, _ = PersonTag.objects.filter(person=person, tag_id=tag_id).delete()
        if not deleted:
            raise ValidationError({"tag_id": "Not attached."})
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrganizationTagView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def post(self, request, org_id):
        org = get_object_or_404(
            Organization.objects.filter(workspace=self.get_workspace()),
            pk=org_id,
        )
        serializer = TagAttachSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tag = serializer.resolve_tag(self.get_workspace())
        OrganizationTag.objects.get_or_create(organization=org, tag=tag)
        return Response(TagSerializer(tag).data, status=status.HTTP_201_CREATED)

    def delete(self, request, org_id, tag_id):
        org = get_object_or_404(
            Organization.objects.filter(workspace=self.get_workspace()),
            pk=org_id,
        )
        deleted, _ = OrganizationTag.objects.filter(
            organization=org, tag_id=tag_id
        ).delete()
        if not deleted:
            raise ValidationError({"tag_id": "Not attached."})
        return Response(status=status.HTTP_204_NO_CONTENT)


class SegmentListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        segments = Segment.objects.filter(workspace=self.get_workspace())
        return Response(SegmentSerializer(segments, many=True).data)

    def post(self, request):
        serializer = SegmentWriteSerializer(
            data=request.data, context={"workspace": self.get_workspace()}
        )
        serializer.is_valid(raise_exception=True)
        segment = serializer.save()
        return Response(SegmentSerializer(segment).data, status=status.HTTP_201_CREATED)


class SegmentDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_object(self, segment_id):
        return get_object_or_404(
            Segment.objects.filter(workspace=self.get_workspace()),
            pk=segment_id,
        )

    def get(self, request, segment_id):
        return Response(SegmentSerializer(self.get_object(segment_id)).data)

    def patch(self, request, segment_id):
        segment = self.get_object(segment_id)
        serializer = SegmentWriteSerializer(
            segment,
            data=request.data,
            partial=True,
            context={"workspace": self.get_workspace()},
        )
        serializer.is_valid(raise_exception=True)
        segment = serializer.save()
        return Response(SegmentSerializer(segment).data)

    def delete(self, request, segment_id):
        self.get_object(segment_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SegmentMembersView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request, segment_id):
        segment = get_object_or_404(
            Segment.objects.filter(workspace=self.get_workspace()),
            pk=segment_id,
        )
        people = list(resolve_segment_people(segment)[:200])
        orgs = list(resolve_segment_organizations(segment)[:200])
        for person in people:
            person._prefetched_memberships = list(
                person.organization_memberships.select_related("organization")
            )
            person._prefetched_tags = list(person.tag_links.select_related("tag"))
        for org in orgs:
            org._prefetched_tags = list(org.tag_links.select_related("tag"))
        return Response(
            {
                "people": PersonSerializer(people, many=True).data,
                "organizations": OrganizationSerializer(orgs, many=True).data,
            }
        )


class CommentListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        qs = CrmComment.objects.filter(workspace=self.get_workspace()).select_related(
            "author"
        )
        person_id = request.query_params.get("person_id")
        org_id = request.query_params.get("organization_id")
        if person_id:
            qs = qs.filter(person_id=person_id)
        if org_id:
            qs = qs.filter(organization_id=org_id)
        return Response(CrmCommentSerializer(qs[:100], many=True).data)

    def post(self, request):
        serializer = CrmCommentWriteSerializer(
            data=request.data,
            context={"workspace": self.get_workspace(), "request": request},
        )
        serializer.is_valid(raise_exception=True)
        comment = serializer.save()
        comment = CrmComment.objects.select_related("author").get(pk=comment.pk)
        return Response(
            CrmCommentSerializer(comment).data, status=status.HTTP_201_CREATED
        )


class CommentDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_object(self, comment_id):
        return get_object_or_404(
            CrmComment.objects.filter(workspace=self.get_workspace()),
            pk=comment_id,
        )

    def delete(self, request, comment_id):
        self.get_object(comment_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AttachmentListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request):
        qs = CrmAttachment.objects.filter(
            workspace=self.get_workspace()
        ).select_related("uploaded_by")
        person_id = request.query_params.get("person_id")
        org_id = request.query_params.get("organization_id")
        if person_id:
            qs = qs.filter(person_id=person_id)
        if org_id:
            qs = qs.filter(organization_id=org_id)
        return Response(CrmAttachmentSerializer(qs[:100], many=True).data)

    def post(self, request):
        workspace = self.get_workspace()
        upload = request.data.get("file") or request.FILES.get("file")
        _validate_upload(upload)
        person_id = request.data.get("person_id") or None
        org_id = request.data.get("organization_id") or None
        if person_id in ("", None) and org_id in ("", None):
            raise ValidationError("person_id or organization_id is required.")
        if person_id not in ("", None) and org_id not in ("", None):
            raise ValidationError("Provide exactly one of person_id or organization_id.")
        person = None
        organization = None
        if person_id not in ("", None):
            person = get_object_or_404(
                Person.objects.filter(workspace=workspace),
                pk=int(person_id),
            )
        if org_id not in ("", None):
            organization = get_object_or_404(
                Organization.objects.filter(workspace=workspace),
                pk=int(org_id),
            )
        attachment = CrmAttachment.objects.create(
            workspace=workspace,
            person=person,
            organization=organization,
            file=upload,
            name=upload.name,
            size=upload.size,
            content_type=getattr(upload, "content_type", "") or "",
            uploaded_by=request.user,
        )
        return Response(
            CrmAttachmentSerializer(attachment).data,
            status=status.HTTP_201_CREATED,
        )


class AttachmentDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_object(self, attachment_id):
        return get_object_or_404(
            CrmAttachment.objects.filter(workspace=self.get_workspace()),
            pk=attachment_id,
        )

    def delete(self, request, attachment_id):
        attachment = self.get_object(attachment_id)
        attachment.file.delete(save=False)
        attachment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
