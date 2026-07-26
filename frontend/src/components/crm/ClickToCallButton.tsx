import { useCallback, useState } from "react";

import { parseApiError } from "../../api/errors";
import type { CrmIntegrationConnector } from "../../api/crm";
import { useCrmApi } from "../../hooks/useCrmApi";

type Props = {
  phone?: string | null;
  personId?: number | null;
  dealId?: number | null;
  note?: string;
  className?: string;
  onDone?: (detail: string) => void;
  onError?: (message: string) => void;
};

let cachedTelephonyId: number | null = null;

export function ClickToCallButton({
  phone,
  personId,
  dealId,
  note,
  className,
  onDone,
  onError,
}: Props) {
  const crmApi = useCrmApi();
  const [busy, setBusy] = useState(false);
  const trimmed = (phone || "").trim();

  const dial = useCallback(async () => {
    if (!crmApi || !trimmed) return;
    setBusy(true);
    try {
      let connectorId = cachedTelephonyId;
      if (!connectorId) {
        const connectors = await crmApi.listConnectors();
        const tel = connectors.find(
          (row: CrmIntegrationConnector) =>
            row.provider === "telephony" && row.is_active !== false,
        );
        if (!tel) {
          throw new Error(
            "Нет активного telephony-коннектора. Добавьте его на /crm-commerce.",
          );
        }
        connectorId = tel.id;
        cachedTelephonyId = tel.id;
      }
      const result = await crmApi.sendConnectorDial(connectorId, {
        to: trimmed,
        note: note || undefined,
        person_id: personId ?? undefined,
        deal_id: dealId ?? undefined,
      });
      onDone?.(
        result.remote
          ? `Звонок на ${trimmed} инициирован (${result.pbx || "pbx"})`
          : `Звонок на ${trimmed} записан локально`,
      );
    } catch (err) {
      cachedTelephonyId = null;
      onError?.(parseApiError(err, "Не удалось позвонить"));
    } finally {
      setBusy(false);
    }
  }, [crmApi, trimmed, note, personId, dealId, onDone, onError]);

  if (!trimmed) return null;

  return (
    <button
      type="button"
      disabled={busy || !crmApi}
      onClick={() => void dial()}
      className={
        className ||
        "rounded-lg border border-border bg-cream px-2.5 py-1 text-xs font-medium text-text hover:bg-surface disabled:opacity-60"
      }
      title={`Позвонить ${trimmed}`}
    >
      {busy ? "Звоним…" : "Позвонить"}
    </button>
  );
}
