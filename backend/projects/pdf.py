from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _fmt(value):
    if value is None:
        return "—"
    return str(value)


def render_status_report_pdf(report: dict) -> bytes:
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
        "ReportTitle",
        parent=styles["Heading1"],
        fontSize=16,
        spaceAfter=8,
    )
    heading = ParagraphStyle(
        "ReportHeading",
        parent=styles["Heading2"],
        fontSize=12,
        spaceBefore=10,
        spaceAfter=6,
    )
    body = styles["BodyText"]

    project = report["project"]
    evm = report.get("evm") or {}
    story = [
        Paragraph(f"Статус-отчёт: {project['name']}", title_style),
        Paragraph(f"Сгенерирован: {_fmt(report.get('generated_at'))}", body),
        Spacer(1, 0.3 * cm),
        Paragraph("Сводка", heading),
    ]

    summary_rows = [
        ["Статус", _fmt(project.get("status"))],
        ["Прогресс", f"{report.get('progress', 0)}%"],
        ["Бюджет", f"{project.get('budget', 0)}"],
        ["Даты", f"{_fmt(project.get('start_date'))} — {_fmt(project.get('end_date'))}"],
        ["SPI / CPI", f"{_fmt(evm.get('spi'))} / {_fmt(evm.get('cpi'))}"],
        ["EV / PV / AC", f"{_fmt(evm.get('earned_value'))} / {_fmt(evm.get('planned_value'))} / {_fmt(evm.get('actual_cost'))}"],
        [
            "Критический путь",
            f"{len((report.get('critical_path') or {}).get('critical_path_ids') or [])} задач, "
            f"длительность {(report.get('critical_path') or {}).get('project_duration', '—')}",
        ],
    ]
    summary = Table(summary_rows, colWidths=[5 * cm, 12 * cm])
    summary.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F5F0E8")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D9D0C3")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(summary)

    charter = report.get("charter") or {}
    story.append(Paragraph("Устав", heading))
    story.append(Paragraph(f"<b>Цели:</b> {_fmt(charter.get('goals')) or '—'}", body))
    story.append(
        Paragraph(
            f"<b>Критерии успеха:</b> {_fmt(charter.get('success_criteria')) or '—'}",
            body,
        )
    )

    story.append(Paragraph("Топ риски", heading))
    risks = report.get("top_risks") or []
    if not risks:
        story.append(Paragraph("Открытых рисков нет.", body))
    else:
        risk_rows = [["Риск", "Оценка", "Статус"]]
        for risk in risks:
            risk_rows.append(
                [_fmt(risk.get("title")), _fmt(risk.get("score")), _fmt(risk.get("status"))]
            )
        risk_table = Table(risk_rows, colWidths=[10 * cm, 3 * cm, 4 * cm])
        risk_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8DFD2")),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D9D0C3")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.append(risk_table)

    story.append(Paragraph("Вехи", heading))
    milestones = report.get("milestones") or []
    if not milestones:
        story.append(Paragraph("Вех нет.", body))
    else:
        for milestone in milestones:
            story.append(
                Paragraph(
                    f"• {_fmt(milestone.get('code'))} {_fmt(milestone.get('name'))} "
                    f"({_fmt(milestone.get('start_date'))})",
                    body,
                )
            )

    story.append(Paragraph("Стейкхолдеры", heading))
    stakeholders = report.get("stakeholders") or []
    if not stakeholders:
        story.append(Paragraph("Стейкхолдеры не указаны.", body))
    else:
        for person in stakeholders:
            story.append(
                Paragraph(
                    f"• {_fmt(person.get('name'))} — {_fmt(person.get('role'))}",
                    body,
                )
            )

    doc.build(story)
    return buffer.getvalue()
