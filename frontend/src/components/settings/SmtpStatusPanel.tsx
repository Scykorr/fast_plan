import { useCallback, useEffect, useState } from "react";

import { parseApiError } from "../../api/errors";
import type { WorkspaceEmailStatus } from "../../api/workspace";
import { GlossaryText, TermHint } from "../TermHint";
import { useWorkspaceApi } from "../../hooks/useWorkspaceApi";

export function SmtpStatusPanel() {
  const workspaceApi = useWorkspaceApi();
  const [status, setStatus] = useState<WorkspaceEmailStatus | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [to, setTo] = useState("");

  const load = useCallback(async () => {
    if (!workspaceApi) return;
    setError("");
    try {
      setStatus(await workspaceApi.getEmailStatus());
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить статус SMTP"));
    }
  }, [workspaceApi]);

  useEffect(() => {
    void load();
  }, [load]);

  const sendTest = async () => {
    if (!workspaceApi) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const result = await workspaceApi.testEmail(to.trim() || undefined);
      setStatus(result.status);
      setMessage(
        result.ok
          ? `Тест отправлен на ${result.to} (${result.latency_ms} ms)`
          : `Ошибка доставки: ${result.detail}`,
      );
      if (!result.ok) {
        setError(result.detail);
      }
    } catch (err) {
      setError(parseApiError(err, "Не удалось отправить тест"));
    } finally {
      setBusy(false);
    }
  };

  const verifyOnWithoutSmtp =
    Boolean(status?.require_email_verification) && !status?.go_live_ready;

  return (
    <div className="max-w-2xl rounded-xl border border-border bg-surface p-6">
      <h2 className="mb-1 text-lg font-semibold text-text">
        Почта / <TermHint term="smtp">SMTP</TermHint>
      </h2>
      <p className="mb-4 text-sm text-text-muted">
        Статус из переменных окружения сервера. Учётные данные меняются только в{" "}
        <code className="text-xs">.env</code>, не через UI. Чеклист:{" "}
        <code className="text-xs">docs/SMTP.md</code>.
      </p>

      {error && <p className="mb-3 text-sm text-primary">{error}</p>}
      {message && !error && (
        <p className="mb-3 text-sm text-secondary" role="status">
          {message}
        </p>
      )}

      {verifyOnWithoutSmtp && (
        <p className="mb-3 rounded-lg border border-primary/40 bg-primary/5 px-3 py-2 text-sm text-primary">
          Verification включён, но SMTP не готов к go-live — регистрация/логин
          могут ломаться. Верните{" "}
          <code className="text-xs">REQUIRE_EMAIL_VERIFICATION=false</code> или
          настройте боевой SMTP.
        </p>
      )}

      {status && (
        <dl className="grid gap-2 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-xs text-text-muted">Backend</dt>
            <dd className="font-medium text-text break-all">{status.backend}</dd>
          </div>
          <div>
            <dt className="text-xs text-text-muted">Host</dt>
            <dd className="font-medium text-text">
              {status.host || "—"}:{status.port || "—"}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-text-muted">From</dt>
            <dd className="font-medium text-text break-all">
              {status.from_email || "—"}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-text-muted">Флаги</dt>
            <dd className="font-medium text-text">
              {status.is_console
                ? "console"
                : status.configured
                  ? "SMTP"
                  : "не настроено"}
              {" · "}
              TLS {status.use_tls ? "on" : "off"}
              {" · "}
              user {status.host_user_set ? "задан" : "нет"}
              {" · "}
              verify {status.require_email_verification ? "on" : "off"}
            </dd>
          </div>
          <div className="sm:col-span-2">
            <dt className="text-xs text-text-muted">
              <GlossaryText text="Go-live" /> ready
            </dt>
            <dd className="font-medium text-text">
              {status.go_live_ready
                ? "да — можно включать verification после успешного теста"
                : "нет — нужен реальный SMTP + DEFAULT_FROM_EMAIL (не console/locmem)"}
            </dd>
          </div>
        </dl>
      )}

      <div className="mt-4 flex flex-wrap items-end gap-2">
        <label className="flex min-w-[12rem] flex-1 flex-col gap-1 text-sm">
          <span className="text-xs text-text-muted">Кому (пусто = ваш email)</span>
          <input
            type="email"
            value={to}
            onChange={(event) => setTo(event.target.value)}
            placeholder="you@example.com"
            className="rounded-lg border border-border bg-cream px-3 py-2 text-sm text-text"
          />
        </label>
        <button
          type="button"
          disabled={busy || !workspaceApi}
          onClick={() => void sendTest()}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
        >
          {busy ? "Отправка…" : "Отправить тест"}
        </button>
        <button
          type="button"
          disabled={!workspaceApi}
          onClick={() => void load()}
          className="rounded-lg border border-border px-3 py-2 text-sm text-text hover:bg-cream"
        >
          Обновить
        </button>
      </div>
    </div>
  );
}
