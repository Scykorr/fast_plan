"""API views for P6g channels, P6h commerce, P6i analytics."""

from decimal import Decimal

from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from crm.analytics import build_ar_ap_summary, build_crm_analytics
from crm.channels import ingest_telegram_webhook, sync_connection
from crm.commerce_pdf import render_crm_document_pdf
from crm.models import (
    ChannelConnection,
    CrmDocument,
    CrmDocumentPayment,
    CrmSavedReport,
    Deal,
    Organization,
    Person,
)
from crm.serializers import (
    ChannelConnectionSerializer,
    ChannelConnectionWriteSerializer,
    CrmDocumentPaymentSerializer,
    CrmDocumentSerializer,
    CrmDocumentWriteSerializer,
    CrmSavedReportSerializer,
)
from workspaces.mixins import IsWorkspaceEditorOrReadOnly, WorkspaceMixin


class ChannelConnectionListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        rows = ChannelConnection.objects.filter(workspace=self.get_workspace())
        return Response(ChannelConnectionSerializer(rows, many=True).data)

    def post(self, request):
        serializer = ChannelConnectionWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        row = ChannelConnection.objects.create(
            workspace=self.get_workspace(),
            provider=data["provider"],
            name=data["name"],
            is_active=data.get("is_active", True),
            config=data.get("config") or {},
        )
        return Response(
            ChannelConnectionSerializer(row).data, status=status.HTTP_201_CREATED
        )


class ChannelConnectionDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_object(self, connection_id):
        return get_object_or_404(
            ChannelConnection.objects.filter(workspace=self.get_workspace()),
            pk=connection_id,
        )

    def get(self, request, connection_id):
        return Response(ChannelConnectionSerializer(self.get_object(connection_id)).data)

    def patch(self, request, connection_id):
        row = self.get_object(connection_id)
        serializer = ChannelConnectionWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        for field in ("provider", "name", "is_active", "config"):
            if field in data:
                setattr(row, field, data[field])
        row.save()
        return Response(ChannelConnectionSerializer(row).data)

    def delete(self, request, connection_id):
        self.get_object(connection_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChannelConnectionSyncView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def post(self, request, connection_id):
        row = get_object_or_404(
            ChannelConnection.objects.filter(workspace=self.get_workspace()),
            pk=connection_id,
        )
        try:
            result = sync_connection(row)
        except Exception as exc:  # noqa: BLE001
            raise ValidationError({"detail": str(exc)}) from exc
        return Response({"ok": True, **result, "connection": ChannelConnectionSerializer(row).data})


class TelegramWebhookView(APIView):
    """Public webhook: POST /api/crm/channels/telegram/<secret>/"""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, secret):
        connection = (
            ChannelConnection.objects.filter(
                provider=ChannelConnection.Provider.TELEGRAM,
                is_active=True,
            )
            .filter(config__webhook_secret=secret)
            .select_related("workspace")
            .first()
        )
        if connection is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        activity = ingest_telegram_webhook(connection, request.data if isinstance(request.data, dict) else {})
        connection.last_synced_at = timezone.now()
        connection.save(update_fields=["last_synced_at", "updated_at"])
        return Response({"ok": True, "activity_id": activity.id if activity else None})


class CrmDocumentListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        qs = CrmDocument.objects.filter(workspace=self.get_workspace()).select_related(
            "organization", "person", "deal"
        )
        doc_type = request.query_params.get("doc_type")
        status_filter = request.query_params.get("status")
        if doc_type:
            qs = qs.filter(doc_type=doc_type)
        if status_filter:
            qs = qs.filter(status=status_filter)
        return Response(CrmDocumentSerializer(qs[:200], many=True).data)

    def post(self, request):
        serializer = CrmDocumentWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        workspace = self.get_workspace()
        org = None
        person = None
        deal = None
        if data.get("organization_id"):
            org = get_object_or_404(
                Organization.objects.filter(workspace=workspace), pk=data["organization_id"]
            )
        if data.get("person_id"):
            person = get_object_or_404(
                Person.objects.filter(workspace=workspace), pk=data["person_id"]
            )
        if data.get("deal_id"):
            deal = get_object_or_404(
                Deal.objects.filter(workspace=workspace), pk=data["deal_id"]
            )
            if org is None:
                org = deal.organization
            if person is None:
                person = deal.person
        doc = CrmDocument.objects.create(
            workspace=workspace,
            doc_type=data["doc_type"],
            number=data.get("number") or "",
            title=data["title"],
            status=data.get("status") or CrmDocument.Status.DRAFT,
            amount=data.get("amount") or 0,
            currency=data.get("currency") or "RUB",
            body=data.get("body") or "",
            line_items=data.get("line_items") or [],
            issue_date=data.get("issue_date") or timezone.localdate(),
            due_date=data.get("due_date"),
            organization=org,
            person=person,
            deal=deal,
            created_by=request.user if request.user.is_authenticated else None,
        )
        return Response(CrmDocumentSerializer(doc).data, status=status.HTTP_201_CREATED)


class CrmDocumentDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_object(self, document_id):
        return get_object_or_404(
            CrmDocument.objects.filter(workspace=self.get_workspace()).select_related(
                "organization", "person", "deal"
            ),
            pk=document_id,
        )

    def get(self, request, document_id):
        return Response(CrmDocumentSerializer(self.get_object(document_id)).data)

    def patch(self, request, document_id):
        doc = self.get_object(document_id)
        serializer = CrmDocumentWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        for field in (
            "doc_type",
            "number",
            "title",
            "status",
            "amount",
            "currency",
            "body",
            "line_items",
            "issue_date",
            "due_date",
        ):
            if field in data:
                setattr(doc, field, data[field])
        if "organization_id" in data:
            oid = data["organization_id"]
            doc.organization = (
                get_object_or_404(Organization.objects.filter(workspace=doc.workspace), pk=oid)
                if oid
                else None
            )
        if "person_id" in data:
            pid = data["person_id"]
            doc.person = (
                get_object_or_404(Person.objects.filter(workspace=doc.workspace), pk=pid)
                if pid
                else None
            )
        if "deal_id" in data:
            did = data["deal_id"]
            doc.deal = (
                get_object_or_404(Deal.objects.filter(workspace=doc.workspace), pk=did)
                if did
                else None
            )
        doc.save()
        return Response(CrmDocumentSerializer(doc).data)

    def delete(self, request, document_id):
        self.get_object(document_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CrmDocumentPdfView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def post(self, request, document_id):
        doc = get_object_or_404(
            CrmDocument.objects.filter(workspace=self.get_workspace()).select_related(
                "organization", "person", "deal"
            ),
            pk=document_id,
        )
        pdf_bytes = render_crm_document_pdf(doc)
        filename = f"{doc.doc_type}-{doc.number or doc.id}.pdf"
        doc.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)
        return Response(CrmDocumentSerializer(doc).data)


class CrmDocumentPaymentListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request, document_id):
        doc = get_object_or_404(
            CrmDocument.objects.filter(workspace=self.get_workspace()), pk=document_id
        )
        rows = doc.payments.all()
        return Response(CrmDocumentPaymentSerializer(rows, many=True).data)

    def post(self, request, document_id):
        doc = get_object_or_404(
            CrmDocument.objects.filter(workspace=self.get_workspace()), pk=document_id
        )
        amount = request.data.get("amount")
        paid_at = request.data.get("paid_at") or timezone.localdate().isoformat()
        if amount in (None, ""):
            raise ValidationError({"amount": "Required."})
        payment = CrmDocumentPayment.objects.create(
            document=doc,
            amount=amount,
            paid_at=paid_at,
            notes=request.data.get("notes") or "",
        )
        paid_sum = sum((p.amount for p in doc.payments.all()), start=Decimal("0"))
        if doc.doc_type == CrmDocument.DocType.INVOICE and paid_sum >= doc.amount:
            doc.status = CrmDocument.Status.PAID
            doc.save(update_fields=["status", "updated_at"])
        return Response(
            CrmDocumentPaymentSerializer(payment).data, status=status.HTTP_201_CREATED
        )


class CrmArApView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        return Response(build_ar_ap_summary(self.get_workspace()))


class CrmAnalyticsView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        return Response(build_crm_analytics(self.get_workspace()))


class CrmSavedReportListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        rows = CrmSavedReport.objects.filter(workspace=self.get_workspace())
        return Response(CrmSavedReportSerializer(rows, many=True).data)

    def post(self, request):
        name = (request.data.get("name") or "").strip()
        if not name:
            raise ValidationError({"name": "Required."})
        row = CrmSavedReport.objects.create(
            workspace=self.get_workspace(),
            name=name,
            query=request.data.get("query") or {},
            created_by=request.user if request.user.is_authenticated else None,
        )
        return Response(CrmSavedReportSerializer(row).data, status=status.HTTP_201_CREATED)


class CrmSavedReportDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def delete(self, request, report_id):
        row = get_object_or_404(
            CrmSavedReport.objects.filter(workspace=self.get_workspace()), pk=report_id
        )
        row.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
