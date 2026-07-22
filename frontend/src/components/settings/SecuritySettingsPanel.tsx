import { useCallback, useEffect, useState, type FormEvent } from "react";

import { api, type AuthSessionRow, type User } from "../../api/client";
import { parseApiError } from "../../api/errors";
import { useWorkspace } from "../../context/WorkspaceContext";
import { useWorkspaceApi } from "../../hooks/useWorkspaceApi";

type Props = {
  user: User;
  onUserUpdate: (user: User) => void;
};

export function SecuritySettingsPanel({ user, onUserUpdate }: Props) {
  const { activeWorkspace } = useWorkspace();
  const workspaceApi = useWorkspaceApi();
  const isOwner = activeWorkspace?.role === "owner";

  const [sessions, setSessions] = useState<AuthSessionRow[]>([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [setupSecret, setSetupSecret] = useState("");
  const [setupUrl, setSetupUrl] = useState("");
  const [enableCode, setEnableCode] = useState("");
  const [backupCodes, setBackupCodes] = useState<string[]>([]);
  const [disablePassword, setDisablePassword] = useState("");
  const [disableCode, setDisableCode] = useState("");
  const [ipDraft, setIpDraft] = useState("");
  const [busy, setBusy] = useState(false);

  const loadSessions = useCallback(async () => {
    try {
      setSessions(await api.listAuthSessions());
    } catch (err) {
      setError(parseApiError(err));
    }
  }, []);

  const loadIpAllowlist = useCallback(async () => {
    if (!workspaceApi || !isOwner) {
      return;
    }
    try {
      const data = await workspaceApi.getIpAllowlist();
      setIpDraft((data.ip_allowlist || []).join("\n"));
    } catch (err) {
      setError(parseApiError(err));
    }
  }, [workspaceApi, isOwner]);

  useEffect(() => {
    void loadSessions();
    void loadIpAllowlist();
  }, [loadSessions, loadIpAllowlist]);

  const handleSetup = async () => {
    setError("");
    setMessage("");
    setBusy(true);
    try {
      const data = await api.setup2fa();
      setSetupSecret(data.secret);
      setSetupUrl(data.otpauth_url);
      setBackupCodes([]);
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setBusy(false);
    }
  };

  const handleEnable = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const data = await api.enable2fa(enableCode);
      onUserUpdate(data.user);
      setBackupCodes(data.backup_codes);
      setSetupSecret("");
      setSetupUrl("");
      setEnableCode("");
      setMessage("2FA включена. Сохраните резервные коды.");
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setBusy(false);
    }
  };

  const handleDisable = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const data = await api.disable2fa({
        password: disablePassword,
        code: disableCode,
      });
      onUserUpdate(data.user);
      setDisablePassword("");
      setDisableCode("");
      setBackupCodes([]);
      setMessage("2FA отключена.");
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setBusy(false);
    }
  };

  const handleSaveIp = async (event: FormEvent) => {
    event.preventDefault();
    if (!workspaceApi) {
      return;
    }
    setError("");
    setBusy(true);
    try {
      const list = ipDraft
        .split(/[\n,]+/)
        .map((item) => item.trim())
        .filter(Boolean);
      const data = await workspaceApi.patchIpAllowlist(list);
      setIpDraft((data.ip_allowlist || []).join("\n"));
      setMessage(
        list.length
          ? "IP allowlist сохранён."
          : "IP allowlist очищен (доступ с любых IP).",
      );
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="max-w-2xl rounded-xl border border-border bg-surface p-6">
      <h2 className="mb-1 text-lg font-semibold text-text">Безопасность</h2>
      <p className="mb-4 text-sm text-text-muted">
        2FA (TOTP), активные сессии и IP allowlist workspace
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

      <section className="space-y-3 border-b border-border pb-6">
        <h3 className="text-sm font-semibold text-text">Двухфакторная аутентификация</h3>
        <p className="text-xs text-text-muted">
          Статус: {user.is_totp_enabled ? "включена" : "выключена"}
        </p>
        {!user.is_totp_enabled && (
          <>
            <button
              type="button"
              disabled={busy}
              onClick={() => void handleSetup()}
              className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white hover:bg-primary-hover disabled:opacity-60"
            >
              Настроить 2FA
            </button>
            {setupSecret && (
              <form onSubmit={handleEnable} className="space-y-2 rounded-lg border border-border bg-cream p-3">
                <p className="text-xs text-text-muted">
                  Добавьте секрет в приложение-аутентификатор, затем введите код.
                </p>
                <p className="break-all font-mono text-xs text-text">{setupSecret}</p>
                {setupUrl && (
                  <p className="break-all text-[11px] text-text-muted">{setupUrl}</p>
                )}
                <input
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  required
                  placeholder="Код из приложения"
                  value={enableCode}
                  onChange={(e) => setEnableCode(e.target.value)}
                  className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                />
                <button
                  type="submit"
                  disabled={busy}
                  className="rounded-lg bg-secondary px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-60"
                >
                  Подтвердить и включить
                </button>
              </form>
            )}
          </>
        )}
        {backupCodes.length > 0 && (
          <div className="rounded-lg border border-border bg-cream p-3">
            <p className="mb-2 text-xs font-medium text-text">Резервные коды (один раз):</p>
            <ul className="grid grid-cols-2 gap-1 font-mono text-xs">
              {backupCodes.map((code) => (
                <li key={code}>{code}</li>
              ))}
            </ul>
          </div>
        )}
        {user.is_totp_enabled && (
          <form onSubmit={handleDisable} className="space-y-2">
            <input
              type="password"
              required
              placeholder="Пароль"
              value={disablePassword}
              onChange={(e) => setDisablePassword(e.target.value)}
              className="w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
            <input
              type="text"
              required
              placeholder="Код 2FA или резервный"
              value={disableCode}
              onChange={(e) => setDisableCode(e.target.value)}
              className="w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
            <button
              type="submit"
              disabled={busy}
              className="rounded-lg border border-border px-3 py-1.5 text-sm font-medium text-text hover:bg-cream disabled:opacity-60"
            >
              Отключить 2FA
            </button>
          </form>
        )}
      </section>

      <section className="space-y-3 border-b border-border py-6">
        <div className="flex items-center justify-between gap-2">
          <h3 className="text-sm font-semibold text-text">Активные сессии</h3>
          <button
            type="button"
            className="text-xs font-medium text-primary hover:underline"
            onClick={() =>
              void (async () => {
                setBusy(true);
                try {
                  await api.revokeOtherSessions();
                  await loadSessions();
                  setMessage("Другие сессии отозваны.");
                } catch (err) {
                  setError(parseApiError(err));
                } finally {
                  setBusy(false);
                }
              })()
            }
          >
            Отозвать остальные
          </button>
        </div>
        <ul className="space-y-2">
          {sessions.length === 0 && (
            <li className="text-xs text-text-muted">Нет зарегистрированных сессий.</li>
          )}
          {sessions.map((session) => (
            <li
              key={session.id}
              className="flex items-start justify-between gap-3 rounded-lg border border-border bg-cream px-3 py-2 text-xs"
            >
              <div>
                <p className="font-medium text-text">
                  {session.is_current ? "Текущая · " : ""}
                  {session.ip_address || "IP неизвестен"}
                </p>
                <p className="mt-0.5 text-text-muted line-clamp-2">
                  {session.user_agent || "Unknown agent"}
                </p>
                <p className="mt-0.5 text-text-muted">
                  Последний вход: {new Date(session.last_seen_at).toLocaleString()}
                </p>
              </div>
              {!session.is_current && (
                <button
                  type="button"
                  className="shrink-0 text-primary hover:underline"
                  onClick={() =>
                    void (async () => {
                      try {
                        await api.revokeAuthSession(session.id);
                        await loadSessions();
                      } catch (err) {
                        setError(parseApiError(err));
                      }
                    })()
                  }
                >
                  Отозвать
                </button>
              )}
            </li>
          ))}
        </ul>
      </section>

      {isOwner && (
        <section className="space-y-3 pt-6">
          <h3 className="text-sm font-semibold text-text">IP allowlist workspace</h3>
          <p className="text-xs text-text-muted">
            Один IP или CIDR на строку. Пусто — разрешены все адреса. Применяется к API
            текущего workspace.
          </p>
          <form onSubmit={handleSaveIp} className="space-y-2">
            <textarea
              rows={4}
              value={ipDraft}
              onChange={(e) => setIpDraft(e.target.value)}
              placeholder={"127.0.0.1\n10.0.0.0/8"}
              className="w-full rounded-lg border border-border bg-cream px-3 py-2 font-mono text-xs outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
            <button
              type="submit"
              disabled={busy}
              className="rounded-lg bg-secondary px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-60"
            >
              Сохранить allowlist
            </button>
          </form>
        </section>
      )}
    </div>
  );
}
