"""API for on-demand CRM connectors (Stripe / 1C / WhatsApp / SMS / telephony)."""

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from crm.connectors import (
    CONNECTOR_CATALOG,
    dial_telephony,
    ingest_onec_documents,
    ingest_sms_webhook,
    ingest_stripe_event,
    ingest_telephony_webhook,
    ingest_whatsapp_webhook,
    new_webhook_token,
    send_sms,
    sync_connector,
    verify_connector_webhook,
)
from crm.models import IntegrationConnector
from crm.serializers import (
    IntegrationConnectorSerializer,
    IntegrationConnectorWriteSerializer,
)
from workspaces.mixins import IsWorkspaceEditorOrReadOnly, WorkspaceMixin


class ConnectorCatalogView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        return Response({"providers": CONNECTOR_CATALOG})


class ConnectorListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        rows = IntegrationConnector.objects.filter(workspace=self.get_workspace())
        return Response(IntegrationConnectorSerializer(rows, many=True).data)

    def post(self, request):
        serializer = IntegrationConnectorWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        row = IntegrationConnector.objects.create(
            workspace=self.get_workspace(),
            provider=data["provider"],
            name=data["name"],
            is_active=data.get("is_active", True),
            config=data.get("config") or {},
            webhook_token=new_webhook_token(),
        )
        return Response(
            IntegrationConnectorSerializer(row).data, status=status.HTTP_201_CREATED
        )


class ConnectorDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_object(self, connector_id):
        return get_object_or_404(
            IntegrationConnector.objects.filter(workspace=self.get_workspace()),
            pk=connector_id,
        )

    def get(self, request, connector_id):
        return Response(
            IntegrationConnectorSerializer(self.get_object(connector_id)).data
        )

    def patch(self, request, connector_id):
        row = self.get_object(connector_id)
        serializer = IntegrationConnectorWriteSerializer(
            data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        for field in ("provider", "name", "is_active"):
            if field in data:
                setattr(row, field, data[field])
        if "config" in data:
            merged = dict(row.config or {})
            for key, value in (data["config"] or {}).items():
                if value == "***":
                    continue
                merged[key] = value
            row.config = merged
        if request.data.get("rotate_webhook_token"):
            row.webhook_token = new_webhook_token()
        row.save()
        return Response(IntegrationConnectorSerializer(row).data)

    def delete(self, request, connector_id):
        self.get_object(connector_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ConnectorSyncView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def post(self, request, connector_id):
        row = get_object_or_404(
            IntegrationConnector.objects.filter(workspace=self.get_workspace()),
            pk=connector_id,
        )
        try:
            result = sync_connector(row)
            row.last_synced_at = timezone.now()
            row.last_error = ""
            row.save(update_fields=["last_synced_at", "last_error", "updated_at"])
        except Exception as exc:  # noqa: BLE001 — surface to client
            row.last_error = str(exc)[:2000]
            row.save(update_fields=["last_error", "updated_at"])
            raise ValidationError({"detail": str(exc)}) from exc
        return Response(
            {
                "ok": True,
                **result,
                "connector": IntegrationConnectorSerializer(row).data,
            }
        )


class ConnectorSendView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def post(self, request, connector_id):
        row = get_object_or_404(
            IntegrationConnector.objects.filter(workspace=self.get_workspace()),
            pk=connector_id,
        )
        if row.provider == IntegrationConnector.Provider.SMS:
            to = (request.data.get("to") or "").strip()
            body = (request.data.get("body") or "").strip()
            try:
                result = send_sms(row, to=to, body=body)
            except Exception as exc:  # noqa: BLE001
                raise ValidationError({"detail": str(exc)}) from exc
            return Response({"ok": True, **result})
        if row.provider == IntegrationConnector.Provider.TELEPHONY:
            to = (request.data.get("to") or "").strip()
            note = (request.data.get("note") or request.data.get("body") or "").strip()
            person_id = request.data.get("person_id")
            deal_id = request.data.get("deal_id")
            lead_id = request.data.get("lead_id")
            try:
                result = dial_telephony(
                    row,
                    to=to,
                    note=note,
                    person_id=int(person_id) if person_id else None,
                    deal_id=int(deal_id) if deal_id else None,
                    lead_id=int(lead_id) if lead_id else None,
                )
            except Exception as exc:  # noqa: BLE001
                raise ValidationError({"detail": str(exc)}) from exc
            return Response({"ok": True, **result})
        raise ValidationError(
            {"detail": "Send is only supported for SMS and telephony connectors."}
        )


class ConnectorAriBridgeView(WorkspaceMixin, APIView):
    """Status + config check for live Asterisk ARI WebSocket bridge."""

    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request, connector_id):
        from crm.ari_bridge import bridge_status

        row = get_object_or_404(
            IntegrationConnector.objects.filter(workspace=self.get_workspace()),
            pk=connector_id,
        )
        if row.provider != IntegrationConnector.Provider.TELEPHONY:
            raise ValidationError(
                {"detail": "ARI bridge is only for telephony connectors."}
            )
        return Response({"ok": True, "connector_id": row.id, **bridge_status(row)})


class ConnectorWebhookView(APIView):
    """Public webhook endpoint keyed by connector.webhook_token."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, provider: str, token: str):
        """WhatsApp / Meta webhook verification challenge."""
        row = (
            IntegrationConnector.objects.filter(
                provider=provider, webhook_token=token, is_active=True
            ).first()
        )
        if row is None:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        if provider == IntegrationConnector.Provider.WHATSAPP:
            mode = request.query_params.get("hub.mode")
            verify = request.query_params.get("hub.verify_token")
            challenge = request.query_params.get("hub.challenge")
            expected = (row.config or {}).get("verify_token") or ""
            if mode == "subscribe" and verify == expected and challenge:
                from django.http import HttpResponse

                return HttpResponse(challenge, content_type="text/plain")
        return Response({"ok": True, "provider": provider})

    def post(self, request, provider: str, token: str):
        row = (
            IntegrationConnector.objects.filter(
                provider=provider, webhook_token=token, is_active=True
            )
            .select_related("workspace")
            .first()
        )
        if row is None:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        if not verify_connector_webhook(row, request):
            return Response({"detail": "Invalid secret"}, status=status.HTTP_403_FORBIDDEN)

        payload = request.data
        try:
            if provider == IntegrationConnector.Provider.STRIPE:
                result = ingest_stripe_event(row, payload if isinstance(payload, dict) else {})
            elif provider == IntegrationConnector.Provider.ONEC:
                result = ingest_onec_documents(row, payload)
            elif provider == IntegrationConnector.Provider.WHATSAPP:
                result = ingest_whatsapp_webhook(
                    row, payload if isinstance(payload, dict) else {}
                )
            elif provider == IntegrationConnector.Provider.SMS:
                result = ingest_sms_webhook(
                    row, payload if isinstance(payload, dict) else {}
                )
            elif provider == IntegrationConnector.Provider.TELEPHONY:
                result = ingest_telephony_webhook(
                    row, payload if isinstance(payload, dict) else {}
                )
            else:
                return Response(
                    {"detail": "Unsupported provider"}, status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as exc:  # noqa: BLE001
            row.last_error = str(exc)[:2000]
            row.save(update_fields=["last_error", "updated_at"])
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        row.last_synced_at = timezone.now()
        row.last_error = ""
        row.save(update_fields=["last_synced_at", "last_error", "updated_at"])
        return Response({"ok": True, **result})
