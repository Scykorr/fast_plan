from django.db.models import Sum
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from finance.models import Transaction
from finance.serializers import TransactionSerializer, TransactionWriteSerializer
from projects.models import Project
from workspaces.services import get_user_workspace


class WorkspaceMixin:
    def get_workspace(self):
        workspace = get_user_workspace(self.request.user)
        if workspace is None:
            raise NotFound("Workspace not found.")
        return workspace


class TransactionListCreateView(WorkspaceMixin, APIView):
    def get(self, request):
        transactions = Transaction.objects.filter(workspace=self.get_workspace())
        project_id = request.query_params.get("project_id")
        if project_id:
            transactions = transactions.filter(project_id=project_id)
        return Response(TransactionSerializer(transactions, many=True).data)

    def post(self, request):
        serializer = TransactionWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        project = None
        if data.get("project_id"):
            project = get_object_or_404(
                Project.objects.filter(workspace=self.get_workspace()),
                pk=data["project_id"],
            )
        transaction = Transaction.objects.create(
            workspace=self.get_workspace(),
            project=project,
            title=data["title"],
            amount=data["amount"],
            transaction_type=data.get("transaction_type", Transaction.TransactionType.EXPENSE),
            category=data.get("category", ""),
            transaction_date=data["transaction_date"],
            notes=data.get("notes", ""),
        )
        return Response(
            TransactionSerializer(transaction).data,
            status=status.HTTP_201_CREATED,
        )


class TransactionDetailView(WorkspaceMixin, APIView):
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
        for field in ("title", "amount", "transaction_type", "category", "transaction_date", "notes"):
            if field in data:
                setattr(transaction, field, data[field])
        transaction.save()
        return Response(TransactionSerializer(transaction).data)

    def delete(self, request, transaction_id):
        transaction = self.get_transaction(transaction_id)
        transaction.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


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
