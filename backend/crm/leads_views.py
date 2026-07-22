import csv
import io
from decimal import Decimal, InvalidOperation

from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from crm.automation import (
    build_deal_context,
    build_lead_context,
    run_automations,
)
from crm.models import AutomationRule, Lead, Organization
from crm.serializers import (
    LeadSerializer,
    LeadWriteSerializer,
)
from crm.services import (
    assign_lead_round_robin,
    compute_lead_score,
    convert_lead_to_deal,
    find_duplicate_leads,
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
        raise ValidationError({"assigned_to_id": "User is not a workspace member."})
    return member.user


class LeadListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        workspace = self.get_workspace()
        qs = Lead.objects.filter(workspace=workspace).select_related(
            "assigned_to", "organization", "person", "deal"
        )
        q = (request.query_params.get("q") or "").strip()
        status_filter = (request.query_params.get("status") or "").strip()
        assigned_to = request.query_params.get("assigned_to")
        if q:
            qs = qs.filter(
                Q(full_name__icontains=q)
                | Q(email__icontains=q)
                | Q(phone__icontains=q)
                | Q(company_name__icontains=q)
                | Q(source__icontains=q)
            )
        if status_filter:
            qs = qs.filter(status=status_filter)
        if assigned_to:
            qs = qs.filter(assigned_to_id=assigned_to)
        leads = list(qs[:300])
        # Attach duplicate flags lightly
        payload = []
        for lead in leads:
            data = LeadSerializer(lead).data
            dupes = find_duplicate_leads(
                workspace,
                email=lead.email,
                phone=lead.phone,
                exclude_id=lead.id,
            )
            data["duplicate_ids"] = list(dupes.values_list("id", flat=True)[:10])
            payload.append(data)
        return Response(payload)

    def post(self, request):
        workspace = self.get_workspace()
        serializer = LeadWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if not data.get("full_name"):
            raise ValidationError({"full_name": "This field is required."})

        skip_dedupe = bool(request.data.get("force"))
        dupes = find_duplicate_leads(
            workspace, email=data.get("email", ""), phone=data.get("phone", "")
        )
        if dupes.exists() and not skip_dedupe:
            return Response(
                {
                    "detail": "Possible duplicate lead.",
                    "duplicates": LeadSerializer(dupes[:10], many=True).data,
                },
                status=status.HTTP_409_CONFLICT,
            )

        assigned = None
        if "assigned_to_id" in request.data:
            assigned = _resolve_assignee(workspace, data.get("assigned_to_id"))
        elif request.data.get("assign") == "round_robin":
            assigned = assign_lead_round_robin(workspace)

        organization = None
        if data.get("organization_id"):
            organization = get_object_or_404(
                Organization.objects.filter(workspace=workspace),
                pk=data["organization_id"],
            )

        score = data.get("score")
        if score is None:
            score = compute_lead_score(
                email=data.get("email", ""),
                phone=data.get("phone", ""),
                company_name=data.get("company_name", ""),
                source=data.get("source", ""),
            )

        lead = Lead.objects.create(
            workspace=workspace,
            full_name=data["full_name"],
            email=data.get("email", ""),
            phone=data.get("phone", ""),
            company_name=data.get("company_name", ""),
            source=data.get("source", ""),
            status=data.get("status", Lead.Status.NEW),
            score=score,
            assigned_to=assigned,
            organization=organization,
            notes=data.get("notes", ""),
        )
        run_automations(
            workspace,
            AutomationRule.Trigger.LEAD_CREATED,
            build_lead_context(lead, trigger=AutomationRule.Trigger.LEAD_CREATED),
        )
        lead = Lead.objects.select_related(
            "assigned_to", "organization", "person", "deal"
        ).get(pk=lead.pk)
        return Response(LeadSerializer(lead).data, status=status.HTTP_201_CREATED)


class LeadDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_object(self, lead_id):
        return get_object_or_404(
            Lead.objects.filter(workspace=self.get_workspace()).select_related(
                "assigned_to", "organization", "person", "deal"
            ),
            pk=lead_id,
        )

    def get(self, request, lead_id):
        lead = self.get_object(lead_id)
        data = LeadSerializer(lead).data
        data["duplicate_ids"] = list(
            find_duplicate_leads(
                self.get_workspace(),
                email=lead.email,
                phone=lead.phone,
                exclude_id=lead.id,
            ).values_list("id", flat=True)[:10]
        )
        return Response(data)

    def patch(self, request, lead_id):
        workspace = self.get_workspace()
        lead = self.get_object(lead_id)
        serializer = LeadWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        for field in (
            "full_name",
            "email",
            "phone",
            "company_name",
            "source",
            "status",
            "notes",
        ):
            if field in data:
                setattr(lead, field, data[field])
        if "score" in data:
            lead.score = data["score"]
        elif any(
            field in request.data
            for field in ("email", "phone", "company_name", "source")
        ):
            lead.score = compute_lead_score(
                email=lead.email,
                phone=lead.phone,
                company_name=lead.company_name,
                source=lead.source,
            )
        if "assigned_to_id" in request.data:
            lead.assigned_to = _resolve_assignee(
                workspace, data.get("assigned_to_id")
            )
        if "organization_id" in request.data:
            org_id = data.get("organization_id")
            lead.organization = (
                get_object_or_404(
                    Organization.objects.filter(workspace=workspace), pk=org_id
                )
                if org_id
                else None
            )
        lead.save()
        return Response(LeadSerializer(self.get_object(lead.id)).data)

    def delete(self, request, lead_id):
        self.get_object(lead_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LeadAssignView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def post(self, request, lead_id):
        workspace = self.get_workspace()
        lead = get_object_or_404(
            Lead.objects.filter(workspace=workspace), pk=lead_id
        )
        mode = request.data.get("mode") or "manual"
        if mode == "round_robin":
            user = assign_lead_round_robin(workspace)
            if user is None:
                raise ValidationError("No eligible assignees.")
            lead.assigned_to = user
        else:
            user_id = request.data.get("user_id")
            if user_id is None:
                raise ValidationError({"user_id": "Required for manual assign."})
            lead.assigned_to = _resolve_assignee(workspace, user_id)
        lead.save(update_fields=["assigned_to", "updated_at"])
        return Response(LeadSerializer(lead).data)


class LeadConvertView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def post(self, request, lead_id):
        lead = get_object_or_404(
            Lead.objects.filter(workspace=self.get_workspace()),
            pk=lead_id,
        )
        if lead.status == Lead.Status.CONVERTED and lead.deal_id:
            from crm.serializers import DealSerializer
            from crm.deals_views import _deal_queryset

            deal = _deal_queryset(self.get_workspace()).get(pk=lead.deal_id)
            return Response(
                {"lead": LeadSerializer(lead).data, "deal": DealSerializer(deal).data}
            )
        amount = request.data.get("amount")
        amount_dec = None
        if amount not in (None, ""):
            try:
                amount_dec = Decimal(str(amount))
            except (InvalidOperation, TypeError, ValueError):
                raise ValidationError({"amount": "Invalid amount."})
        try:
            deal = convert_lead_to_deal(
                lead,
                title=request.data.get("title") or None,
                amount=amount_dec,
            )
        except ValueError as exc:
            raise ValidationError(str(exc))
        from crm.deals_views import _deal_queryset
        from crm.serializers import DealSerializer

        workspace = self.get_workspace()
        run_automations(
            workspace,
            AutomationRule.Trigger.LEAD_CONVERTED,
            {
                **build_lead_context(lead, trigger=AutomationRule.Trigger.LEAD_CONVERTED),
                **build_deal_context(deal, trigger=AutomationRule.Trigger.LEAD_CONVERTED),
            },
        )
        run_automations(
            workspace,
            AutomationRule.Trigger.DEAL_CREATED,
            build_deal_context(deal, trigger=AutomationRule.Trigger.DEAL_CREATED),
        )
        deal = _deal_queryset(workspace).get(pk=deal.pk)
        lead = Lead.objects.select_related(
            "assigned_to", "organization", "person", "deal"
        ).get(pk=lead.pk)
        return Response(
            {"lead": LeadSerializer(lead).data, "deal": DealSerializer(deal).data},
            status=status.HTTP_201_CREATED,
        )


class LeadImportView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def post(self, request):
        workspace = self.get_workspace()
        assign_mode = request.data.get("assign") or ""
        force = bool(request.data.get("force"))
        upload = request.FILES.get("file")
        rows = []
        if upload is not None:
            text = upload.read().decode("utf-8-sig", errors="replace")
            reader = csv.DictReader(io.StringIO(text))
            rows = list(reader)
        elif isinstance(request.data.get("leads"), list):
            rows = request.data["leads"]
        else:
            raise ValidationError("Provide CSV file or leads[] JSON.")

        created = 0
        skipped = 0
        duplicates = 0
        errors = []
        for index, row in enumerate(rows, start=1):
            full_name = (
                row.get("full_name")
                or row.get("name")
                or row.get("Name")
                or ""
            ).strip()
            if not full_name:
                errors.append(f"Row {index}: full_name/name required")
                skipped += 1
                continue
            email = (row.get("email") or row.get("Email") or "").strip()
            phone = (row.get("phone") or row.get("Phone") or "").strip()
            company = (
                row.get("company_name")
                or row.get("company")
                or row.get("Company")
                or ""
            ).strip()
            source = (row.get("source") or row.get("Source") or "").strip()
            notes = (row.get("notes") or row.get("Notes") or "").strip()

            dupes = find_duplicate_leads(workspace, email=email, phone=phone)
            if dupes.exists() and not force:
                duplicates += 1
                skipped += 1
                continue

            assigned = None
            if assign_mode == "round_robin":
                assigned = assign_lead_round_robin(workspace)

            Lead.objects.create(
                workspace=workspace,
                full_name=full_name,
                email=email,
                phone=phone,
                company_name=company,
                source=source,
                notes=notes,
                score=compute_lead_score(
                    email=email,
                    phone=phone,
                    company_name=company,
                    source=source,
                ),
                assigned_to=assigned,
            )
            created += 1

        return Response(
            {
                "created": created,
                "skipped": skipped,
                "duplicates": duplicates,
                "errors": errors[:50],
            }
        )
