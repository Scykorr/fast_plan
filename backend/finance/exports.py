"""CSV / XLSX export helpers for finance transactions."""

import csv
import io

from django.http import HttpResponse

TRANSACTION_HEADERS = [
    "id",
    "title",
    "amount",
    "transaction_type",
    "category",
    "transaction_date",
    "project_id",
    "notes",
]

XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _transaction_rows(transactions) -> list[dict]:
    return [
        {
            "id": transaction.id,
            "title": transaction.title,
            "amount": str(transaction.amount),
            "transaction_type": transaction.transaction_type,
            "category": transaction.category,
            "transaction_date": transaction.transaction_date.isoformat(),
            "project_id": transaction.project_id or "",
            "notes": transaction.notes,
        }
        for transaction in transactions
    ]


def render_transactions_csv(transactions) -> HttpResponse:
    rows = _transaction_rows(transactions)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="transactions.csv"'
    writer = csv.DictWriter(response, fieldnames=TRANSACTION_HEADERS)
    writer.writeheader()
    writer.writerows(rows)
    return response


def render_transactions_xlsx(transactions) -> HttpResponse:
    import openpyxl

    rows = _transaction_rows(transactions)
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Transactions"
    sheet.append(TRANSACTION_HEADERS)
    for row in rows:
        sheet.append([row[header] for header in TRANSACTION_HEADERS])
    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type=XLSX_CONTENT_TYPE)
    response["Content-Disposition"] = 'attachment; filename="transactions.xlsx"'
    return response
