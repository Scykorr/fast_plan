"""Guest commercial portal: share links for CRM documents."""

from __future__ import annotations

import secrets
from decimal import Decimal

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from crm.commerce_pdf import render_crm_document_pdf
from crm.models import CrmDocument, CrmDocumentShareLink
from workspaces.mixins import IsWorkspaceEditorOrReadOnly, WorkspaceMixin


def _paid_total(document: CrmDocument) -> Decimal:
    return sum((p.amount for p in document.payments.all()), start=Decimal("0"))


def _payment_status(amount: Decimal, paid_total: Decimal) -> str:
    if paid_total <= 0:
        return "unpaid"
    if paid_total >= amount:
        return "paid"
    return "partial"


def _public_payload(link: CrmDocumentShareLink) -> dict:
    doc = link.document
    paid_total = _paid_total(doc)
    amount = Decimal(doc.amount or 0)
    balance_due = max(amount - paid_total, Decimal("0"))
    payments = [
        {
            "amount": str(p.amount),
            "paid_at": p.paid_at,
            "currency": doc.currency,
        }
        for p in doc.payments.all().order_by("paid_at", "id")
    ]
    return {
        "share": {
            "label": link.label,
            "allow_approve": link.allow_approve,
            "allow_pdf": link.allow_pdf,
            "workspace_name": doc.workspace.name,
        },
        "document": {
            "id": doc.id,
            "doc_type": doc.doc_type,
            "number": doc.number,
            "title": doc.title,
            "status": doc.status,
            "amount": str(doc.amount),
            "currency": doc.currency,
            "body": doc.body,
            "line_items": doc.line_items or [],
            "issue_date": doc.issue_date,
            "due_date": doc.due_date,
            "organization_name": doc.organization.name if doc.organization_id else None,
            "person_name": doc.person.full_name if doc.person_id else None,
            "paid_total": str(paid_total),
            "balance_due": str(balance_due),
            "payment_status": _payment_status(amount, paid_total),
            "payments": payments,
            "can_approve": link.allow_approve
            and doc.status
            in (
                CrmDocument.Status.DRAFT,
                CrmDocument.Status.SENT,
            ),
        },
    }


def _active_link(token: str) -> CrmDocumentShareLink:
    link = (
        CrmDocumentShareLink.objects.select_related(
            "document",
            "document__workspace",
            "document__organization",
            "document__person",
        )
        .prefetch_related("document__payments")
        .filter(token=token)
        .first()
    )
    if link is None or not link.is_active:
        raise NotFound("Share link not found or expired.")
    return link


def _serialize_link(link: CrmDocumentShareLink) -> dict:
    return {
        "id": link.id,
        "token": link.token,
        "label": link.label,
        "created_at": link.created_at,
        "expires_at": link.expires_at,
        "last_accessed_at": link.last_accessed_at,
        "is_active": link.is_active,
        "allow_approve": link.allow_approve,
        "allow_pdf": link.allow_pdf,
        "url_path": f"/commerce/{link.token}",
    }


class CrmDocumentShareLinkListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request, document_id):
        doc = get_object_or_404(
            CrmDocument.objects.filter(workspace=self.get_workspace()),
            pk=document_id,
        )
        links = doc.share_links.filter(revoked_at__isnull=True)
        return Response([_serialize_link(link) for link in links])

    def post(self, request, document_id):
        doc = get_object_or_404(
            CrmDocument.objects.filter(workspace=self.get_workspace()),
            pk=document_id,
        )
        expires_raw = request.data.get("expires_at")
        expires_at = None
        if expires_raw:
            expires_at = timezone.datetime.fromisoformat(
                str(expires_raw).replace("Z", "+00:00")
            )
            if timezone.is_naive(expires_at):
                expires_at = timezone.make_aware(expires_at)
        link = CrmDocumentShareLink.objects.create(
            document=doc,
            token=secrets.token_urlsafe(24),
            label=str(request.data.get("label", "")).strip()[:100],
            created_by=request.user,
            expires_at=expires_at,
            allow_approve=bool(request.data.get("allow_approve", True)),
            allow_pdf=bool(request.data.get("allow_pdf", True)),
        )
        return Response(_serialize_link(link), status=status.HTTP_201_CREATED)


class CrmDocumentShareLinkDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def delete(self, request, document_id, link_id):
        doc = get_object_or_404(
            CrmDocument.objects.filter(workspace=self.get_workspace()),
            pk=document_id,
        )
        link = get_object_or_404(doc.share_links, pk=link_id)
        link.revoked_at = timezone.now()
        link.save(update_fields=["revoked_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class PublicCrmDocumentShareView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, token):
        link = _active_link(token)
        link.last_accessed_at = timezone.now()
        link.save(update_fields=["last_accessed_at"])
        return Response(_public_payload(link))


class PublicCrmDocumentApproveView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, token):
        link = _active_link(token)
        if not link.allow_approve:
            raise ValidationError({"detail": "Approve is not allowed for this link."})
        doc = link.document
        if doc.status not in (CrmDocument.Status.DRAFT, CrmDocument.Status.SENT):
            raise ValidationError(
                {"detail": f"Document status '{doc.status}' cannot be approved."}
            )
        doc.status = CrmDocument.Status.ACCEPTED
        doc.save(update_fields=["status", "updated_at"])
        link.last_accessed_at = timezone.now()
        link.save(update_fields=["last_accessed_at"])
        return Response(_public_payload(link))


class PublicCrmDocumentPdfView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, token):
        link = _active_link(token)
        if not link.allow_pdf:
            raise ValidationError({"detail": "PDF is not allowed for this link."})
        doc = link.document
        pdf_bytes = render_crm_document_pdf(doc)
        filename = f"{doc.doc_type}-{doc.number or doc.id}.pdf"
        link.last_accessed_at = timezone.now()
        link.save(update_fields=["last_accessed_at"])
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        return response
