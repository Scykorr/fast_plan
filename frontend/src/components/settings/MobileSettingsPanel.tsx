import { useEffect, useState } from "react";

import { fetchVapidPublicKey, subscribeWebPush, unsubscribeWebPush } from "../../api/webPush";
import { parseApiError } from "../../api/errors";

export function MobileSettingsPanel() {
  const [configured, setConfigured] = useState(false);
  const [supported, setSupported] = useState(false);
  const [permission, setPermission] = useState<NotificationPermission | "unknown">(
    "unknown",
  );
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const pushOk =
      typeof window !== "undefined" &&
      "serviceWorker" in navigator &&
      "PushManager" in window &&
      "Notification" in window;
    setSupported(pushOk);
    if (pushOk) {
      setPermission(Notification.permission);
    }
    void (async () => {
      try {
        const vapid = await fetchVapidPublicKey();
        setConfigured(vapid.configured);
      } catch {
        setConfigured(false);
      }
    })();
  }, []);

  return (
    <div className="max-w-2xl rounded-xl border border-border bg-surface p-6">
      <h2 className="mb-1 text-lg font-semibold text-text">Мобильное / PWA</h2>
      <p className="mb-4 text-sm text-text-muted">
        Push-уведомления и офлайн-очередь CRM-активностей и задач сделок
      </p>

      {error && (
        <p className="mb-3 text-sm text-primary" role="alert">
          {error}
        </p>
      )}
      {message && (
        <p className="mb-3 text-sm text-secondary" role="status">
          {message}
        </p>
      )}

      <section className="space-y-2 text-sm">
        <p className="text-text-muted">
          Push:{" "}
          {!supported
            ? "браузер не поддерживает"
            : !configured
              ? "сервер без VAPID (см. generate_vapid_keys)"
              : `готово · разрешение: ${permission}`}
        </p>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={busy || !supported || !configured}
            className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white hover:bg-primary-hover disabled:opacity-60"
            onClick={() =>
              void (async () => {
                setBusy(true);
                setError("");
                setMessage("");
                try {
                  const result = await subscribeWebPush();
                  if (result.ok) {
                    setPermission("granted");
                    setMessage("Push включён на этом устройстве.");
                  } else {
                    setError(result.reason || "Не удалось подписаться.");
                  }
                } catch (err) {
                  setError(parseApiError(err));
                } finally {
                  setBusy(false);
                }
              })()
            }
          >
            Включить push
          </button>
          <button
            type="button"
            disabled={busy || !supported}
            className="rounded-lg border border-border px-3 py-1.5 text-sm font-medium text-text hover:bg-cream disabled:opacity-60"
            onClick={() =>
              void (async () => {
                setBusy(true);
                setError("");
                try {
                  await unsubscribeWebPush();
                  setMessage("Push отключён на этом устройстве.");
                  if ("Notification" in window) {
                    setPermission(Notification.permission);
                  }
                } catch (err) {
                  setError(parseApiError(err));
                } finally {
                  setBusy(false);
                }
              })()
            }
          >
            Отключить push
          </button>
        </div>
        <p className="text-xs text-text-muted">
          Офлайн: при создании активности/задачи без сети запись попадает в очередь
          (баннер слева внизу) и уходит после появления связи.
        </p>
      </section>
    </div>
  );
}
