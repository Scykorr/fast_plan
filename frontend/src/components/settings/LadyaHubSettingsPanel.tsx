import { useCallback, useEffect, useState } from "react";

import { parseApiError } from "../../api/errors";
import { ErrorMessage } from "../ErrorMessage";
import { useWorkspace } from "../../context/WorkspaceContext";
import { useLadyaApi } from "../../hooks/useLadyaApi";

export function LadyaHubSettingsPanel() {
  const api = useLadyaApi();
  const { workspaceEpoch, activeWorkspace } = useWorkspace();
  const [enabled, setEnabled] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    if (!api) return;
    setLoading(true);
    try {
      const settings = await api.getSettings();
      setEnabled(settings.ladya_hub_enabled);
      setError("");
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить настройки Ладьи"));
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => {
    void load();
  }, [load, workspaceEpoch]);

  const toggle = async () => {
    if (!api) return;
    setSaving(true);
    setMessage("");
    try {
      const next = !enabled;
      const settings = await api.patchSettings({ ladya_hub_enabled: next });
      setEnabled(settings.ladya_hub_enabled);
      setMessage(
        settings.ladya_hub_enabled
          ? "Контур «Ладья» включён — раздел появится в сайдбаре."
          : "Контур «Ладья» выключен.",
      );
    } catch (err) {
      setError(parseApiError(err, "Не удалось сохранить флаг Ладьи"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="rounded-xl border border-border bg-surface p-5 space-y-3">
      <div>
        <h2 className="text-lg font-semibold text-text">Ладья (операционный контур)</h2>
        <p className="mt-1 text-sm text-text-muted">
          Feature-flag для workspace
          {activeWorkspace ? ` «${activeWorkspace.name}»` : ""}. По умолчанию выключен.
        </p>
      </div>
      {error && <ErrorMessage message={error} onDismiss={() => setError("")} />}
      {message && <p className="text-sm text-primary">{message}</p>}
      {loading ? (
        <p className="text-sm text-text-muted">Загрузка...</p>
      ) : (
        <label className="flex items-center gap-3 text-sm">
          <input
            type="checkbox"
            checked={enabled}
            disabled={saving}
            onChange={() => void toggle()}
          />
          <span>Включить раздел «Ладья» (ladya_hub_enabled)</span>
        </label>
      )}
    </section>
  );
}
