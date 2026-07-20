"""CSV import for finance transactions (same headers as export)."""

import csv
import io
from datetime import date
from decimal import Decimal, InvalidOperation

from django.db import transaction

from finance.exports import TRANSACTION_HEADERS
from finance.models import Transaction
from projects.models import Project


def _decode_csv(raw: bytes) -> list[dict]:
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("CSV file is empty.")
    required = ("title", "amount", "transaction_date")
    missing = [header for header in required if header not in reader.fieldnames]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    return [dict(row) for row in reader]


@transaction.atomic
def import_transactions_csv(workspace, raw: bytes) -> dict:
    rows = _decode_csv(raw)
    created = 0
    errors: list[str] = []

    for index, row in enumerate(rows, start=2):
        title = (row.get("title") or "").strip()
        amount_raw = (row.get("amount") or "").strip()
        date_raw = (row.get("transaction_date") or "").strip()
        if not title or not amount_raw or not date_raw:
            errors.append(f"Row {index}: title, amount and transaction_date are required.")
            continue
        try:
            amount = Decimal(amount_raw)
        except (InvalidOperation, ValueError):
            errors.append(f"Row {index}: invalid amount '{amount_raw}'.")
            continue
        try:
            transaction_date = date.fromisoformat(date_raw)
        except ValueError:
            errors.append(f"Row {index}: invalid date '{date_raw}'.")
            continue

        tx_type = (row.get("transaction_type") or Transaction.TransactionType.EXPENSE).strip()
        if tx_type not in Transaction.TransactionType.values:
            tx_type = Transaction.TransactionType.EXPENSE

        project = None
        project_id = (row.get("project_id") or "").strip()
        if project_id:
            project = Project.objects.filter(workspace=workspace, pk=project_id).first()
            if project is None:
                errors.append(f"Row {index}: project_id {project_id} not found.")
                continue

        Transaction.objects.create(
            workspace=workspace,
            project=project,
            title=title,
            amount=amount,
            transaction_type=tx_type,
            category=(row.get("category") or "").strip(),
            transaction_date=transaction_date,
            notes=(row.get("notes") or "").strip(),
        )
        created += 1

    return {
        "created": created,
        "errors": errors,
        "headers": TRANSACTION_HEADERS,
    }
