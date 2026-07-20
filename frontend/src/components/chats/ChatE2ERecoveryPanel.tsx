import { useCallback, useEffect, useState } from "react";

import { parseApiError } from "../../api/errors";
import { ErrorMessage } from "../ErrorMessage";
import { useAuth } from "../../context/AuthContext";
import { useChatsApi } from "../../hooks/useChatsApi";
import {
  acknowledgeRecoveryPhrase,
  createRecoveryBackup,
  ensureIdentity,
  generateRecoveryPhrase,
  hasAcknowledgedRecoveryPhrase,
  hasLocalIdentity,
  normalizeRecoveryPhrase,
  restoreFromRecoveryBackup,
  validateRecoveryPhrase,
} from "../../utils/chatE2E";

export function ChatE2ERecoveryPanel() {
  const { user } = useAuth();
  const chatsApi = useChatsApi();
  const [hasRecovery, setHasRecovery] = useState(false);
  const [hasLocal, setHasLocal] = useState(false);
  const [ack, setAck] = useState(false);
  const [draftPhrase, setDraftPhrase] = useState("");
  const [confirmPhrase, setConfirmPhrase] = useState("");
  const [restorePhrase, setRestorePhrase] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [step, setStep] = useState<"idle" | "create" | "restore">("idle");

  const refresh = useCallback(async () => {
    if (!chatsApi || !user) {
      return;
    }
    setHasLocal(hasLocalIdentity(user.id));
    setAck(hasAcknowledgedRecoveryPhrase(user.id));
    try {
      const me = await chatsApi.getMyCryptoKey();
      setHasRecovery(Boolean(me.has_recovery));
      if (!me.public_jwk && !hasLocalIdentity(user.id)) {
        const identity = await ensureIdentity(user.id);
        await chatsApi.putMyPublicKey(identity.publicJwk);
        setHasLocal(true);
      }
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить E2E-состояние"));
    }
  }, [chatsApi, user]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  if (!user || !chatsApi) {
    return null;
  }

  const startCreate = () => {
    setError("");
    setMessage("");
    setDraftPhrase(generateRecoveryPhrase());
    setConfirmPhrase("");
    setStep("create");
  };

  const saveBackup = async () => {
    if (normalizeRecoveryPhrase(confirmPhrase) !== normalizeRecoveryPhrase(draftPhrase)) {
      setError("Подтверждение фразы не совпадает.");
      return;
    }
    if (!validateRecoveryPhrase(draftPhrase)) {
      setError("Некорректная фраза.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const backup = await createRecoveryBackup(user.id, draftPhrase);
      await chatsApi.putMyPublicKey(backup.publicJwk, {
        recovery_blob: backup.recovery_blob,
        recovery_salt: backup.recovery_salt,
      });
      acknowledgeRecoveryPhrase(user.id);
      setAck(true);
      setHasRecovery(true);
      setHasLocal(true);
      setStep("idle");
      setDraftPhrase("");
      setConfirmPhrase("");
      setMessage(
        "Фраза сохранения записана. Храните её офлайн — без неё новый браузер не расшифрует DM.",
      );
    } catch (err) {
      setError(parseApiError(err, "Не удалось сохранить backup"));
    } finally {
      setBusy(false);
    }
  };

  const doRestore = async () => {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const me = await chatsApi.getMyCryptoKey();
      if (!me.recovery_blob || !me.recovery_salt) {
        throw new Error("На сервере нет recovery backup. Создайте фразу на исходном устройстве.");
      }
      const publicJwk = await restoreFromRecoveryBackup({
        userId: user.id,
        phrase: restorePhrase,
        recovery_blob: me.recovery_blob,
        recovery_salt: me.recovery_salt,
      });
      await chatsApi.putMyPublicKey(publicJwk);
      setHasLocal(true);
      setAck(true);
      setStep("idle");
      setRestorePhrase("");
      setMessage("Ключ восстановлен на этом устройстве. Можно открывать зашифрованные DM.");
    } catch (err) {
      setError(
        err instanceof Error && err.name === "OperationError"
          ? "Неверная фраза восстановления."
          : err instanceof Error
            ? err.message
            : parseApiError(err, "Не удалось восстановить ключ"),
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="max-w-lg rounded-xl border border-border bg-surface p-6">
      <h2 className="mb-2 text-lg font-semibold text-text">E2E ключи чатов</h2>
      <p className="mb-4 text-sm text-text-muted">
        Приватный ключ DM хранится только в браузере. Фраза восстановления позволяет
        синхронизировать его на другом устройстве.
      </p>
      <ul className="mb-4 space-y-1 text-sm text-text">
        <li>Локальный ключ: {hasLocal ? "есть" : "нет"}</li>
        <li>Backup на сервере: {hasRecovery ? "есть" : "нет"}</li>
        <li>Фраза подтверждена: {ack ? "да" : "нет"}</li>
      </ul>

      {step === "idle" && (
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={startCreate}
            className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white hover:bg-primary-hover"
          >
            {hasRecovery ? "Пересоздать фразу" : "Создать фразу восстановления"}
          </button>
          <button
            type="button"
            onClick={() => {
              setStep("restore");
              setError("");
              setMessage("");
            }}
            className="rounded-lg border border-border bg-cream px-3 py-1.5 text-sm font-medium text-text"
          >
            Восстановить на этом устройстве
          </button>
        </div>
      )}

      {step === "create" && (
        <div className="space-y-3">
          <p className="text-sm font-medium text-text">Запишите фразу (12 слов):</p>
          <p className="rounded-lg border border-border bg-cream p-3 font-mono text-sm leading-relaxed text-text">
            {draftPhrase}
          </p>
          <label className="block text-xs text-text-muted">
            Введите фразу ещё раз для подтверждения
            <textarea
              value={confirmPhrase}
              onChange={(event) => setConfirmPhrase(event.target.value)}
              rows={2}
              className="mt-1 w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm"
            />
          </label>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={busy}
              onClick={() => void saveBackup()}
              className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-60"
            >
              {busy ? "…" : "Сохранить backup"}
            </button>
            <button
              type="button"
              onClick={() => setStep("idle")}
              className="rounded-lg border border-border px-3 py-1.5 text-sm text-text-muted"
            >
              Отмена
            </button>
          </div>
        </div>
      )}

      {step === "restore" && (
        <div className="space-y-3">
          <label className="block text-xs text-text-muted">
            Фраза восстановления
            <textarea
              value={restorePhrase}
              onChange={(event) => setRestorePhrase(event.target.value)}
              rows={2}
              placeholder="twelve words …"
              className="mt-1 w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm"
            />
          </label>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={busy || !restorePhrase.trim()}
              onClick={() => void doRestore()}
              className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-60"
            >
              {busy ? "…" : "Восстановить"}
            </button>
            <button
              type="button"
              onClick={() => setStep("idle")}
              className="rounded-lg border border-border px-3 py-1.5 text-sm text-text-muted"
            >
              Отмена
            </button>
          </div>
        </div>
      )}

      {message && <p className="mt-3 text-sm text-secondary">{message}</p>}
      {error && (
        <div className="mt-3">
          <ErrorMessage message={error} onDismiss={() => setError("")} />
        </div>
      )}
    </div>
  );
}
