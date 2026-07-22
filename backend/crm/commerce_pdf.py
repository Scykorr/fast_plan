"""PDF rendering for CRM commercial documents."""

from __future__ import annotations

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _fmt(value) -> str:
    if value is None or value == "":
        return "—"
    return str(value)


def render_crm_document_pdf(document) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CrmDocTitle", parent=styles["Heading1"], fontSize=16, spaceAfter=8
    )
    heading = ParagraphStyle(
        "CrmDocHeading",
        parent=styles["Heading2"],
        fontSize=12,
        spaceBefore=10,
        spaceAfter=6,
    )
    body = styles["BodyText"]

    type_labels = {
        "quote": "Коммерческое предложение",
        "invoice": "Счёт",
        "contract": "Договор",
    }
    story = [
        Paragraph(
            f"{type_labels.get(document.doc_type, document.doc_type)} "
            f"{_fmt(document.number)}",
            title_style,
        ),
        Paragraph(document.title, body),
        Spacer(1, 0.3 * cm),
    ]

    meta_rows = [
        ["Статус", _fmt(document.status)],
        ["Сумма", f"{document.amount} {document.currency}"],
        ["Клиент", _fmt(document.organization.name if document.organization_id else None)],
        ["Контакт", _fmt(document.person.full_name if document.person_id else None)],
        ["Сделка", _fmt(document.deal.title if document.deal_id else None)],
        ["Дата", _fmt(document.issue_date)],
        ["Срок оплаты", _fmt(document.due_date)],
    ]
    meta = Table(meta_rows, colWidths=[4.5 * cm, 12.5 * cm])
    meta.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E8F0F8")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B8C9DA")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(meta)

    items = document.line_items or []
    if items:
        story.append(Paragraph("Позиции", heading))
        rows = [["Наименование", "Кол-во", "Цена", "Сумма"]]
        for item in items:
            if not isinstance(item, dict):
                continue
            qty = item.get("qty") or item.get("quantity") or 1
            price = item.get("price") or item.get("unit_price") or 0
            try:
                line_sum = float(qty) * float(price)
            except (TypeError, ValueError):
                line_sum = item.get("amount") or 0
            rows.append(
                [
                    _fmt(item.get("title") or item.get("name")),
                    _fmt(qty),
                    _fmt(price),
                    _fmt(line_sum),
                ]
            )
        table = Table(rows, colWidths=[8 * cm, 2.5 * cm, 3 * cm, 3.5 * cm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3B82F6")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B8C9DA")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(table)

    if document.body:
        story.append(Paragraph("Текст", heading))
        for paragraph in str(document.body).split("\n"):
            story.append(Paragraph(_fmt(paragraph) or "&nbsp;", body))

    doc.build(story)
    return buffer.getvalue()
