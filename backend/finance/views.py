from django.db.models import Sum
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import log_audit
from crm.models import Deal, Organization
from finance.imports import import_transactions_csv
from finance.exports import render_transactions_csv, render_transactions_xlsx
from finance.models import Transaction
from finance.serializers import TransactionSerializer, TransactionWriteSerializer
from projects.models import Project
from workspaces.mixins import IsWorkspaceEditorOrReadOnly, WorkspaceMixin
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.exceptions import ValidationError


class TransactionListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        transactions = Transaction.objects.filter(
            workspace=self.get_workspace()
        ).select_related("organization", "deal", "project")
        project_id = request.query_params.get("project_id")
        organization_id = request.query_params.get("organization_id")
        deal_id = request.query_params.get("deal_id")
        if project_id:
            transactions = transactions.filter(project_id=project_id)
        if organization_id:
            transactions = transactions.filter(organization_id=organization_id)
        if deal_id:
            transactions = transactions.filter(deal_id=deal_id)
        return Response(TransactionSerializer(transactions, many=True).data)

    def post(self, request):
        serializer = TransactionWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        workspace = self.get_workspace()
        project = None
        if data.get("project_id"):
            project = get_object_or_404(
                Project.objects.filter(workspace=workspace),
                pk=data["project_id"],
            )
        organization = None
        if data.get("organization_id"):
            organization = get_object_or_404(
                Organization.objects.filter(workspace=workspace),
                pk=data["organization_id"],
            )
        deal = None
        if data.get("deal_id"):
            deal = get_object_or_404(
                Deal.objects.filter(workspace=workspace),
                pk=data["deal_id"],
            )
            if organization is None and deal.organization_id:
                organization = deal.organization
        transaction = Transaction.objects.create(
            workspace=workspace,
            project=project,
            organization=organization,
            deal=deal,
            title=data["title"],
            amount=data["amount"],
            transaction_type=data.get("transaction_type", Transaction.TransactionType.EXPENSE),
            category=data.get("category", ""),
            transaction_date=data["transaction_date"],
            notes=data.get("notes", ""),
        )
        log_audit(
            workspace,
            request.user,
            "transaction.create",
            "Transaction",
            transaction.id,
            summary=f"{transaction.transaction_type}: {transaction.title} ({transaction.amount})",
            changes={"title": transaction.title, "amount": str(transaction.amount)},
        )
        return Response(
            TransactionSerializer(transaction).data,
            status=status.HTTP_201_CREATED,
        )


class TransactionDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_transaction(self, transaction_id):
        return get_object_or_404(
            Transaction.objects.filter(workspace=self.get_workspace()),
            pk=transaction_id,
        )

    def patch(self, request, transaction_id):
        transaction = self.get_transaction(transaction_id)
        serializer = TransactionWriteSerializer(
            transaction, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if "project_id" in data:
            project = None
            if data["project_id"]:
                project = get_object_or_404(
                    Project.objects.filter(workspace=self.get_workspace()),
                    pk=data["project_id"],
                )
            transaction.project = project
        if "organization_id" in data:
            organization = None
            if data["organization_id"]:
                organization = get_object_or_404(
                    Organization.objects.filter(workspace=self.get_workspace()),
                    pk=data["organization_id"],
                )
            transaction.organization = organization
        if "deal_id" in data:
            deal = None
            if data["deal_id"]:
                deal = get_object_or_404(
                    Deal.objects.filter(workspace=self.get_workspace()),
                    pk=data["deal_id"],
                )
            transaction.deal = deal
        for field in ("title", "amount", "transaction_type", "category", "transaction_date", "notes"):
            if field in data:
                setattr(transaction, field, data[field])
        transaction.save()
        log_audit(
            self.get_workspace(),
            request.user,
            "transaction.update",
            "Transaction",
            transaction.id,
            summary=f"Updated transaction: {transaction.title}",
            changes={key: str(value) for key, value in data.items()},
        )
        return Response(TransactionSerializer(transaction).data)

    def delete(self, request, transaction_id):
        transaction = self.get_transaction(transaction_id)
        log_audit(
            self.get_workspace(),
            request.user,
            "transaction.delete",
            "Transaction",
            transaction.id,
            summary=f"Deleted transaction: {transaction.title}",
            changes={"title": transaction.title, "amount": str(transaction.amount)},
        )
        transaction.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TransactionExportView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def perform_content_negotiation(self, request, force=False):
        # The view returns a raw HttpResponse (CSV/XLSX), so DRF's renderer
        # negotiation is irrelevant here. Since we also accept ?format=csv|xlsx
        # as a query param, we must bypass DRF's reserved `format` query param
        # handling (URL_FORMAT_OVERRIDE), which would otherwise raise Http404
        # when no renderer is registered for "csv"/"xlsx".
        renderer = self.get_renderers()[0]
        return renderer, renderer.media_type

    def get(self, request):
        transactions = Transaction.objects.filter(workspace=self.get_workspace())
        project_id = request.query_params.get("project_id")
        if project_id:
            transactions = transactions.filter(project_id=project_id)
        fmt = (request.query_params.get("format") or request.query_params.get("output") or "csv").lower()
        if fmt == "xlsx":
            return render_transactions_xlsx(transactions)
        return render_transactions_csv(transactions)


class TransactionImportView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        upload = request.FILES.get("file")
        if upload is None:
            raise ValidationError({"file": "CSV file is required."})
        try:
            result = import_transactions_csv(self.get_workspace(), upload.read())
        except ValueError as exc:
            raise ValidationError({"file": str(exc)}) from exc
        return Response(result)


class ProjectFinanceSummaryView(WorkspaceMixin, APIView):
    def get(self, request, project_id):
        project = get_object_or_404(
            Project.objects.filter(workspace=self.get_workspace()),
            pk=project_id,
        )
        transactions = Transaction.objects.filter(project=project)
        expenses = transactions.filter(
            transaction_type=Transaction.TransactionType.EXPENSE
        ).aggregate(total=Sum("amount"))["total"] or 0
        income = transactions.filter(
            transaction_type=Transaction.TransactionType.INCOME
        ).aggregate(total=Sum("amount"))["total"] or 0
        return Response(
            {
                "project_id": project.id,
                "budget": float(project.budget or 0),
                "actual_expenses": float(expenses),
                "actual_income": float(income),
                "balance": float(project.budget or 0) - float(expenses) + float(income),
                "transactions": TransactionSerializer(transactions, many=True).data,
            }
        )
