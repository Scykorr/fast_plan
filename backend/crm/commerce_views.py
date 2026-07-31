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

from crm.analytics import (
    build_ar_ap_summary,
    build_cashflow_forecast,
    build_crm_analytics,
    build_crm_pnl,
    report_to_csv_rows,
    run_crm_report,
)
from crm.channels import (
    ingest_instagram_webhook,
    ingest_telegram_webhook,
    ingest_vk_callback,
    sync_connection,
)
from crm.commerce_pdf import render_crm_document_pdf
from crm.inventory import line_items_total, normalize_line_items, sync_document_stock_on_status_change
from crm.models import (
    ChannelConnection,
    CrmDocument,
    CrmDocumentPayment,
    CrmSavedFilter,
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
    CrmSavedFilterSerializer,
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


class InstagramWebhookView(APIView):
    """Public Meta Instagram webhook: GET verify + POST events.

    URL secret is `config.webhook_secret` (same pattern as Telegram).
    Meta hub.verify_token must match `config.verify_token`.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def _connection(self, secret):
        return (
            ChannelConnection.objects.filter(
                provider=ChannelConnection.Provider.INSTAGRAM,
                is_active=True,
                config__webhook_secret=secret,
            )
            .select_related("workspace")
            .first()
        )

    def get(self, request, secret):
        connection = self._connection(secret)
        if connection is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        mode = request.query_params.get("hub.mode")
        token = request.query_params.get("hub.verify_token")
        challenge = request.query_params.get("hub.challenge")
        expected = (connection.config or {}).get("verify_token") or ""
        if mode == "subscribe" and expected and token == expected and challenge:
            from django.http import HttpResponse

            return HttpResponse(challenge, content_type="text/plain")
        return Response({"detail": "Verification failed"}, status=status.HTTP_403_FORBIDDEN)

    def post(self, request, secret):
        connection = self._connection(secret)
        if connection is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        created = ingest_instagram_webhook(
            connection, request.data if isinstance(request.data, dict) else {}
        )
        connection.last_synced_at = timezone.now()
        connection.save(update_fields=["last_synced_at", "updated_at"])
        return Response({"ok": True, "created": created})


class VkCallbackView(APIView):
    """Public VK Callback API: POST /api/crm/channels/vk/<secret>/"""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, secret):
        connection = (
            ChannelConnection.objects.filter(
                provider=ChannelConnection.Provider.VK,
                is_active=True,
            )
            .filter(config__secret=secret)
            .select_related("workspace")
            .first()
        )
        if connection is None:
            # also allow matching by webhook path secret stored as verify key
            connection = (
                ChannelConnection.objects.filter(
                    provider=ChannelConnection.Provider.VK,
                    is_active=True,
                    config__webhook_secret=secret,
                )
                .select_related("workspace")
                .first()
            )
        if connection is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            confirmation, created = ingest_vk_callback(
                connection, request.data if isinstance(request.data, dict) else {}
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        connection.last_synced_at = timezone.now()
        connection.save(update_fields=["last_synced_at", "updated_at"])
        if confirmation is not None:
            from django.http import HttpResponse

            return HttpResponse(confirmation, content_type="text/plain")
        return Response({"ok": True, "created": created})


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
        line_items = normalize_line_items(workspace, data.get("line_items") or [])
        amount = data.get("amount")
        if amount in (None, "") or data.get("recompute_amount"):
            computed = line_items_total(line_items)
            if computed > 0 or data.get("recompute_amount"):
                amount = computed
            else:
                amount = data.get("amount") or 0
        doc = CrmDocument.objects.create(
            workspace=workspace,
            doc_type=data["doc_type"],
            number=data.get("number") or "",
            title=data["title"],
            status=data.get("status") or CrmDocument.Status.DRAFT,
            amount=amount or 0,
            currency=data.get("currency") or "RUB",
            body=data.get("body") or "",
            line_items=line_items,
            issue_date=data.get("issue_date") or timezone.localdate(),
            due_date=data.get("due_date"),
            organization=org,
            person=person,
            deal=deal,
            created_by=request.user if request.user.is_authenticated else None,
        )
        sync_document_stock_on_status_change(
            doc, previous_status=CrmDocument.Status.DRAFT, user=request.user
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
        previous_status = doc.status
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
            "issue_date",
            "due_date",
        ):
            if field in data:
                setattr(doc, field, data[field])
        if "line_items" in data:
            doc.line_items = normalize_line_items(doc.workspace, data["line_items"] or [])
            if "amount" not in data or data.get("recompute_amount"):
                doc.amount = line_items_total(doc.line_items)
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
        sync_document_stock_on_status_change(
            doc, previous_status=previous_status, user=request.user
        )
        doc.refresh_from_db()
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
        from datetime import date as date_cls

        from finance.models import Transaction

        if isinstance(paid_at, str):
            paid_date = date_cls.fromisoformat(paid_at)
        else:
            paid_date = paid_at
        tx_type = Transaction.TransactionType.INCOME
        if doc.doc_type == CrmDocument.DocType.BILL:
            tx_type = Transaction.TransactionType.EXPENSE
        tx = Transaction.objects.create(
            workspace=doc.workspace,
            organization=doc.organization,
            deal=doc.deal,
            project=doc.project,
            title=f"CRM {doc.doc_type} #{doc.number or doc.id}: {doc.title}",
            amount=amount,
            transaction_type=tx_type,
            category="crm_payment",
            transaction_date=paid_date,
            notes=request.data.get("notes") or "",
        )
        payment = CrmDocumentPayment.objects.create(
            document=doc,
            amount=amount,
            paid_at=paid_at,
            notes=request.data.get("notes") or "",
            finance_transaction=tx,
        )
        paid_sum = sum((p.amount for p in doc.payments.all()), start=Decimal("0"))
        if (
            doc.doc_type
            in (CrmDocument.DocType.INVOICE, CrmDocument.DocType.BILL)
            and paid_sum >= doc.amount
        ):
            doc.status = CrmDocument.Status.PAID
            doc.save(update_fields=["status", "updated_at"])
        return Response(
            CrmDocumentPaymentSerializer(payment).data, status=status.HTTP_201_CREATED
        )


class CrmArApView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        return Response(build_ar_ap_summary(self.get_workspace()))


class CrmPnlView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        org_id = request.query_params.get("organization_id")
        deal_id = request.query_params.get("deal_id")
        return Response(
            build_crm_pnl(
                self.get_workspace(),
                organization_id=int(org_id) if org_id else None,
                deal_id=int(deal_id) if deal_id else None,
            )
        )


class CrmCashflowForecastView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        days = request.query_params.get("days") or 90
        try:
            days_int = int(days)
        except (TypeError, ValueError):
            days_int = 90
        return Response(
            build_cashflow_forecast(self.get_workspace(), horizon_days=days_int)
        )


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


class CrmReportRunView(WorkspaceMixin, APIView):
    """POST run builder query; GET ?format=csv exports last-style query from body not available — use POST."""

    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def post(self, request):
        query = request.data.get("query") or request.data or {}
        if not isinstance(query, dict):
            raise ValidationError({"query": "Object required"})
        # allow {query: {...}} or flat metric/filters
        if "metric" not in query and "query" in request.data:
            query = request.data["query"]
        result = run_crm_report(self.get_workspace(), query)
        export = (
            (request.query_params.get("export") or request.query_params.get("format") or "")
            .lower()
        )
        if export == "csv" or request.data.get("format") == "csv" or request.data.get("export") == "csv":
            import csv
            from django.http import HttpResponse

            rows = report_to_csv_rows(result)
            resp = HttpResponse(content_type="text/csv; charset=utf-8")
            resp["Content-Disposition"] = 'attachment; filename="crm-report.csv"'
            writer = csv.writer(resp)
            writer.writerows(rows)
            return resp
        return Response(result)


class CrmSavedFilterListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        qs = CrmSavedFilter.objects.filter(
            workspace=self.get_workspace(), user=request.user
        )
        target = request.query_params.get("target")
        if target:
            qs = qs.filter(target=target)
        return Response(CrmSavedFilterSerializer(qs, many=True).data)

    def post(self, request):
        name = (request.data.get("name") or "").strip()
        target = (request.data.get("target") or "").strip()
        if not name:
            raise ValidationError({"name": "Required."})
        if target not in dict(CrmSavedFilter.Target.choices):
            raise ValidationError({"target": "Invalid target."})
        row = CrmSavedFilter.objects.create(
            workspace=self.get_workspace(),
            user=request.user,
            target=target,
            name=name,
            params=request.data.get("params") or {},
        )
        return Response(
            CrmSavedFilterSerializer(row).data, status=status.HTTP_201_CREATED
        )


class CrmSavedFilterDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def patch(self, request, filter_id):
        row = get_object_or_404(
            CrmSavedFilter.objects.filter(
                workspace=self.get_workspace(), user=request.user
            ),
            pk=filter_id,
        )
        if "name" in request.data:
            row.name = (request.data.get("name") or row.name).strip() or row.name
        if "params" in request.data:
            row.params = request.data.get("params") or {}
        row.save()
        return Response(CrmSavedFilterSerializer(row).data)

    def delete(self, request, filter_id):
        row = get_object_or_404(
            CrmSavedFilter.objects.filter(
                workspace=self.get_workspace(), user=request.user
            ),
            pk=filter_id,
        )
        row.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
