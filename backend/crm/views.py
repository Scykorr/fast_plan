from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from crm.models import Activity, Organization, Person, ProjectPersonLink
from crm.serializers import (
    ActivitySerializer,
    ActivityWriteSerializer,
    OrganizationSerializer,
    OrganizationWriteSerializer,
    PersonSerializer,
    PersonWriteSerializer,
    ProjectPersonLinkSerializer,
    ProjectPersonLinkWriteSerializer,
)
from crm.services import sync_project_stakeholders, sync_workspace_contacts
from projects.models import Project
from workspaces.mixins import IsWorkspaceEditorOrReadOnly, IsWorkspaceMember, WorkspaceMixin


class OrganizationListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_queryset(self):
        return (
            Organization.objects.filter(workspace=self.get_workspace())
            .annotate(
                people_count=Count("memberships", distinct=True),
                projects_count=Count("client_projects", distinct=True),
            )
            .order_by("name", "id")
        )

    def get(self, request):
        q = (request.query_params.get("q") or "").strip()
        qs = self.get_queryset()
        if q:
            qs = qs.filter(name__icontains=q)
        return Response(OrganizationSerializer(qs, many=True).data)

    def post(self, request):
        serializer = OrganizationWriteSerializer(
            data=request.data, context={"workspace": self.get_workspace()}
        )
        serializer.is_valid(raise_exception=True)
        org = serializer.save()
        org.people_count = 0
        org.projects_count = 0
        return Response(
            OrganizationSerializer(org).data, status=status.HTTP_201_CREATED
        )


class OrganizationDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_object(self, org_id):
        return get_object_or_404(self.get_queryset_base(), pk=org_id)

    def get_queryset_base(self):
        return Organization.objects.filter(workspace=self.get_workspace()).annotate(
            people_count=Count("memberships", distinct=True),
            projects_count=Count("client_projects", distinct=True),
        )

    def get(self, request, org_id):
        return Response(OrganizationSerializer(self.get_object(org_id)).data)

    def patch(self, request, org_id):
        org = self.get_object(org_id)
        serializer = OrganizationWriteSerializer(org, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        org = serializer.save()
        org = self.get_queryset_base().get(pk=org.pk)
        return Response(OrganizationSerializer(org).data)

    def delete(self, request, org_id):
        self.get_object(org_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PersonListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        q = (request.query_params.get("q") or "").strip()
        qs = (
            Person.objects.filter(workspace=self.get_workspace())
            .annotate(projects_count=Count("project_links", distinct=True))
            .prefetch_related("organization_memberships__organization")
            .order_by("full_name", "id")
        )
        if q:
            from django.db.models import Q

            qs = qs.filter(
                Q(full_name__icontains=q)
                | Q(email__icontains=q)
                | Q(phone__icontains=q)
                | Q(job_title__icontains=q)
            )
        people = list(qs[:200])
        for person in people:
            person._prefetched_memberships = list(person.organization_memberships.all())
        return Response(PersonSerializer(people, many=True).data)

    def post(self, request):
        serializer = PersonWriteSerializer(
            data=request.data, context={"workspace": self.get_workspace()}
        )
        serializer.is_valid(raise_exception=True)
        person = serializer.save()
        person.projects_count = 0
        person._prefetched_memberships = list(
            person.organization_memberships.select_related("organization")
        )
        return Response(PersonSerializer(person).data, status=status.HTTP_201_CREATED)


class PersonDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_object(self, person_id):
        return get_object_or_404(
            Person.objects.filter(workspace=self.get_workspace()).annotate(
                projects_count=Count("project_links", distinct=True)
            ),
            pk=person_id,
        )

    def get(self, request, person_id):
        person = self.get_object(person_id)
        person._prefetched_memberships = list(
            person.organization_memberships.select_related("organization")
        )
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
