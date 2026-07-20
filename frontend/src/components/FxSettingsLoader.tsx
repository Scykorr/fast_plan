import { useEffect } from "react";

import type { Currency } from "../context/LocaleContext";
import { useLocale } from "../context/LocaleContext";
import { useWorkspace } from "../context/WorkspaceContext";
import { useWorkspaceApi } from "../hooks/useWorkspaceApi";

export function FxSettingsLoader() {
  const workspaceApi = useWorkspaceApi();
  const { workspaceEpoch } = useWorkspace();
  const { setFxConfig } = useLocale();

  useEffect(() => {
    if (!workspaceApi) {
      setFxConfig({ baseCurrency: "RUB", rates: { RUB: 1 } });
      return;
    }
    void workspaceApi
      .getSettings()
      .then((data) => {
        const base = data.currency as Currency;
        const rates: Partial<Record<Currency, number>> = { [base]: 1 };
        for (const row of data.exchange_rates) {
          if (row.currency && row.rate_to_base) {
            rates[row.currency as Currency] = Number(row.rate_to_base);
          }
        }
        setFxConfig({ baseCurrency: base, rates });
      })
      .catch(() => {
        setFxConfig({ baseCurrency: "RUB", rates: { RUB: 1 } });
      });
  }, [workspaceApi, workspaceEpoch, setFxConfig]);

  return null;
}
