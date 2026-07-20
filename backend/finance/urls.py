from django.urls import path

from finance.views import (
    ProjectFinanceSummaryView,
    TransactionDetailView,
    TransactionExportView,
    TransactionImportView,
    TransactionListCreateView,
)

urlpatterns = [
    path("finance/transactions/", TransactionListCreateView.as_view(), name="transaction-list"),
    path(
        "finance/transactions/export/",
        TransactionExportView.as_view(),
        name="transaction-export",
    ),
    path(
        "finance/transactions/import/",
        TransactionImportView.as_view(),
        name="transaction-import",
    ),
    path(
        "finance/transactions/<int:transaction_id>/",
        TransactionDetailView.as_view(),
        name="transaction-detail",
    ),
    path(
        "projects/<int:project_id>/finance/",
        ProjectFinanceSummaryView.as_view(),
        name="project-finance",
    ),
]
