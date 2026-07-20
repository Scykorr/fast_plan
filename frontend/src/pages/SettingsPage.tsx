import { useCallback, useEffect, useState, type FormEvent } from "react";

import { api } from "../api/client";
import { parseApiError } from "../api/errors";
import type {
  ExchangeRateRow,
  WebhookEndpoint,
  WorkspaceAPIToken,
  WorkspaceInvitation,
  WorkspaceMember,
  WorkspaceSettings,
} from "../api/workspace";
import { ErrorMessage } from "../components/ErrorMessage";
import { InviteMemberForm } from "../components/workspace/InviteMemberForm";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import { useLocale, type Currency, type Locale } from "../context/LocaleContext";
import { useWorkspace } from "../context/WorkspaceContext";
import { useWorkspaceApi } from "../hooks/useWorkspaceApi";

export function SettingsPage() {
  const { user, updateProfile, logout } = useAuth();
  const { preference, setTheme } = useTheme();
  const { locale, currency, baseCurrency, setLocale, setCurrency, setFxConfig } = useLocale();
  const { activeWorkspace, workspaces, switchWorkspace, workspaceEpoch } =
    useWorkspace();
  const workspaceApi = useWorkspaceApi();
  const [members, setMembers] = useState<WorkspaceMember[]>([]);
  const [invitations, setInvitations] = useState<WorkspaceInvitation[]>([]);
  const [error, setError] = useState("");
  const [copiedToken, setCopiedToken] = useState<string | null>(null);
  const [showInviteForm, setShowInviteForm] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [passwordMessage, setPasswordMessage] = useState("");
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [profileUsername, setProfileUsername] = useState(user?.username ?? "");
  const [profileFirstName, setProfileFirstName] = useState(user?.first_name ?? "");
  const [profileLastName, setProfileLastName] = useState(user?.last_name ?? "");
  const [profileAvatar, setProfileAvatar] = useState<File | null>(null);
  const [profileMessage, setProfileMessage] = useState("");
  const [profileLoading, setProfileLoading] = useState(false);
  const [apiTokens, setApiTokens] = useState<WorkspaceAPIToken[]>([]);
  const [webhooks, setWebhooks] = useState<WebhookEndpoint[]>([]);
  const [tokenName, setTokenName] = useState("");
  const [tokenCanWrite, setTokenCanWrite] = useState(false);
  const [revealedToken, setRevealedToken] = useState("");
  const [webhookName, setWebhookName] = useState("");
  const [webhookUrl, setWebhookUrl] = useState("");
  const [revealedSecret, setRevealedSecret] = useState("");
  const [verificationMessage, setVerificationMessage] = useState("");
  const [verificationLoading, setVerificationLoading] = useState(false);
  const [webhookTestMessage, setWebhookTestMessage] = useState("");
  const [wsSettings, setWsSettings] = useState<WorkspaceSettings | null>(null);
  const [baseCurrencyDraft, setBaseCurrencyDraft] = useState("RUB");
  const [fxCurrency, setFxCurrency] = useState("USD");
  const [fxRate, setFxRate] = useState("");
  const [fxAsOf, setFxAsOf] = useState(() => new Date().toISOString().slice(0, 10));

  useEffect(() => {
    setProfileUsername(user?.username ?? "");
    setProfileFirstName(user?.first_name ?? "");
    setProfileLastName(user?.last_name ?? "");
  }, [user]);

  const load = useCallback(async () => {
    if (!workspaceApi) {
      return;
    }
    try {
      const [membersData, invitationsData] = await Promise.all([
        workspaceApi.getMembers(),
        workspaceApi.getInvitations(),
      ]);
      setMembers(membersData);
      setInvitations(invitationsData);
      if (activeWorkspace?.role === "owner") {
        const [tokenData, webhookData, settingsData] = await Promise.all([
          workspaceApi.getApiTokens(),
          workspaceApi.getWebhooks(),
          workspaceApi.getSettings(),
        ]);
        setApiTokens(tokenData);
        setWebhooks(webhookData);
        setWsSettings(settingsData);
        setBaseCurrencyDraft(settingsData.currency);
        const rates: Partial<Record<Currency, number>> = {
          [settingsData.currency as Currency]: 1,
        };
        for (const row of settingsData.exchange_rates) {
          if (row.currency && row.rate_to_base) {
            rates[row.currency as Currency] = Number(row.rate_to_base);
          }
        }
        setFxConfig({
          baseCurrency: settingsData.currency as Currency,
          rates,
        });
      } else {
        setApiTokens([]);
        setWebhooks([]);
        setWsSettings(null);
      }
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить workspace"));
    }
  }, [workspaceApi, activeWorkspace?.role, setFxConfig]);

  useEffect(() => {
    void load();
  }, [load, activeWorkspace?.id, workspaceEpoch]);

  const copyInviteLink = async (token: string) => {
    const url = `${window.location.origin}/invite/${token}`;
    try {
      await navigator.clipboard.writeText(url);
      setCopiedToken(token);
    } catch {
      setError("Не удалось скопировать ссылку — скопируйте вручную из поля ниже");
    }
  };

  const handleChangePassword = async (event: FormEvent) => {
    event.preventDefault();
    setPasswordMessage("");
    setError("");
    if (newPassword.length < 8) {
      setError("Новый пароль должен быть не короче 8 символов.");
      return;
    }
    setPasswordLoading(true);
    try {
      await api.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      setCurrentPassword("");
      setNewPassword("");
      setPasswordMessage("Пароль изменён. Войдите снова.");
      await logout();
    } catch (err) {
      setError(parseApiError(err, "Не удалось сменить пароль"));
    } finally {
      setPasswordLoading(false);
    }
  };

  const handleProfileSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    setProfileMessage("");
    setProfileLoading(true);
    const formData = new FormData();
    formData.append("username", profileUsername);
    formData.append("first_name", profileFirstName);
    formData.append("last_name", profileLastName);
    if (profileAvatar) {
      formData.append("avatar", profileAvatar);
    }
    try {
      await updateProfile(formData);
      setProfileAvatar(null);
      setProfileMessage("Профиль сохранён.");
    } catch (err) {
      setError(parseApiError(err, "Не удалось сохранить профиль"));
    } finally {
      setProfileLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-text">Настройки</h1>
        <p className="mt-1 text-sm text-text-muted">Профиль и workspace</p>
      </div>

      {error && <ErrorMessage message={error} onDismiss={() => setError("")} />}

      <div className="max-w-lg rounded-xl border border-border bg-surface p-6">
        <h2 className="text-lg font-semibold text-text">Оформление</h2>
        <p className="mt-1 text-sm text-text-muted">
          Светлая — мягкий синий к белому; тёмная — спокойный серый; «Как в
          системе» следует OS и обновляется при смене предпочтения.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          {(["light", "dark", "system"] as const).map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => setTheme(value)}
              className={[
                "rounded-lg border px-4 py-2 text-sm font-medium",
                preference === value
                  ? "border-primary bg-primary text-white"
                  : "border-border bg-cream text-text hover:border-primary",
              ].join(" ")}
            >
              {value === "light"
                ? "Светлая"
                : value === "dark"
                  ? "Тёмная"
                  : "Как в системе"}
            </button>
          ))}
        </div>
        <div className="mt-5 grid grid-cols-2 gap-3">
          <label className="text-xs text-text-muted">
            Язык интерфейса
            <select
              value={locale}
              onChange={(event) => setLocale(event.target.value as Locale)}
              className="mt-1 w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm text-text"
            >
              <option value="ru">Русский</option>
              <option value="en">English (beta)</option>
            </select>
          </label>
          <label className="text-xs text-text-muted">
            Валюта отображения
            <select
              value={currency}
              onChange={(event) => setCurrency(event.target.value as Currency)}
              className="mt-1 w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm text-text"
            >
              <option value="RUB">RUB — ₽</option>
              <option value="USD">USD — $</option>
              <option value="EUR">EUR — €</option>
            </select>
          </label>
        </div>
        {currency !== baseCurrency && (
          <p className="mt-3 text-xs text-text-muted">
            Суммы хранятся в базовой валюте workspace ({baseCurrency}) и
            конвертируются по последним курсам.
          </p>
        )}
      </div>

      <div className="max-w-lg rounded-xl border border-border bg-surface p-6">
        <h2 className="mb-4 text-lg font-semibold text-text">Профиль</h2>
        <form onSubmit={handleProfileSubmit} className="space-y-3">
          <div className="flex items-center gap-4">
            <div className="flex h-16 w-16 items-center justify-center overflow-hidden rounded-full border border-border bg-cream text-lg font-semibold text-primary">
              {user?.avatar_url ? (
                <img
                  src={user.avatar_url}
                  alt="Аватар"
                  className="h-full w-full object-cover"
                />
              ) : (
                (user?.first_name || user?.username || "?").slice(0, 1).toUpperCase()
              )}
            </div>
            <div>
              <label htmlFor="profile-avatar" className="block text-xs text-text-muted">
                Аватар (до 2 МБ)
              </label>
              <input
                id="profile-avatar"
                type="file"
                accept="image/*"
                onChange={(event) =>
                  setProfileAvatar(event.target.files?.[0] ?? null)
                }
                className="mt-1 max-w-xs text-xs text-text-muted"
              />
            </div>
          </div>
          <div>
            <label htmlFor="profile-email" className="mb-1 block text-xs text-text-muted">
              Email
            </label>
            <div className="flex flex-wrap items-center gap-2">
              <input
                id="profile-email"
                value={user?.email ?? ""}
                readOnly
                className="min-w-0 flex-1 rounded-lg border border-border bg-cream px-3 py-2 text-sm text-text-muted"
              />
              {user?.is_email_verified ? (
                <span className="whitespace-nowrap text-xs text-secondary">
                  Подтверждён
                </span>
              ) : (
                <button
                  type="button"
                  disabled={verificationLoading}
                  onClick={async () => {
                    if (!user?.email) {
                      return;
                    }
                    setVerificationLoading(true);
                    setVerificationMessage("");
                    try {
                      const result = await api.resendVerification(user.email);
                      setVerificationMessage(result.detail);
                    } catch (err) {
                      setVerificationMessage(
                        parseApiError(err, "Не удалось отправить письмо"),
                      );
                    } finally {
                      setVerificationLoading(false);
                    }
                  }}
                  className="whitespace-nowrap rounded-lg border border-primary px-3 py-1.5 text-xs font-medium text-primary hover:bg-primary/10 disabled:opacity-60"
                >
                  {verificationLoading ? "Отправка..." : "Подтвердить email"}
                </button>
              )}
            </div>
            {!user?.is_email_verified && verificationMessage && (
              <p className="mt-1 text-xs text-text-muted">{verificationMessage}</p>
            )}
            {!user?.is_email_verified && (
              <p className="mt-1 text-xs text-primary">
                Проверьте почту и перейдите по ссылке из письма для подтверждения.
              </p>
            )}
          </div>
          <div>
            <label htmlFor="profile-username" className="mb-1 block text-xs text-text-muted">
              Имя пользователя
            </label>
            <input
              id="profile-username"
              required
              value={profileUsername}
              onChange={(event) => setProfileUsername(event.target.value)}
              className="w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="profile-first-name" className="mb-1 block text-xs text-text-muted">
                Имя
              </label>
              <input
                id="profile-first-name"
                value={profileFirstName}
                onChange={(event) => setProfileFirstName(event.target.value)}
                className="w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
              />
            </div>
            <div>
              <label htmlFor="profile-last-name" className="mb-1 block text-xs text-text-muted">
                Фамилия
              </label>
              <input
                id="profile-last-name"
                value={profileLastName}
                onChange={(event) => setProfileLastName(event.target.value)}
                className="w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
              />
            </div>
          </div>
          {profileMessage && (
            <p className="text-sm text-secondary" role="status">
              {profileMessage}
            </p>
          )}
          <button
            type="submit"
            disabled={profileLoading}
            className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white hover:bg-primary-hover disabled:opacity-60"
          >
            {profileLoading ? "Сохранение..." : "Сохранить профиль"}
          </button>
        </form>

        <form onSubmit={handleChangePassword} className="mt-6 space-y-3" noValidate>
          <h3 className="text-sm font-semibold text-text">Смена пароля</h3>
          <div>
            <label htmlFor="current-password" className="mb-1 block text-xs text-text-muted">
              Текущий пароль
            </label>
            <input
              id="current-password"
              type="password"
              required
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              className="w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
          </div>
          <div>
            <label htmlFor="new-password" className="mb-1 block text-xs text-text-muted">
              Новый пароль
            </label>
            <input
              id="new-password"
              type="password"
              required
              minLength={8}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
          </div>
          {passwordMessage && (
            <p className="text-sm text-secondary" role="status">
              {passwordMessage}
            </p>
          )}
          <button
            type="submit"
            disabled={passwordLoading}
            className="rounded-lg bg-secondary px-3 py-1.5 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-60"
          >
            {passwordLoading ? "Сохранение..." : "Сменить пароль"}
          </button>
        </form>
      </div>

      <div className="max-w-2xl rounded-xl border border-border bg-surface p-6">
        <h2 className="mb-4 text-lg font-semibold text-text">Workspace</h2>
        <p className="mb-3 text-sm text-text-muted">
          Активный:{" "}
          <span className="font-medium text-text">
            {activeWorkspace?.name ?? "—"}
          </span>
          {activeWorkspace ? ` · ${activeWorkspace.role}` : ""}
        </p>
        {workspaces.length > 1 && (
          <div className="mb-4 flex flex-wrap gap-2">
            {workspaces.map((workspace) => (
              <button
                key={workspace.id}
                type="button"
                onClick={() => void switchWorkspace(workspace.id)}
                className={[
                  "rounded-lg border px-3 py-1.5 text-sm",
                  workspace.id === activeWorkspace?.id
                    ? "border-primary bg-cream text-primary"
                    : "border-border text-text-muted hover:bg-cream",
                ].join(" ")}
              >
                {workspace.name}
              </button>
            ))}
          </div>
        )}

        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-text">Участники</h3>
          <button
            type="button"
            onClick={() => setShowInviteForm((value) => !value)}
            className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white hover:bg-primary-hover"
          >
            {showInviteForm ? "Скрыть" : "Пригласить"}
          </button>
        </div>

        {showInviteForm && (
          <div className="mb-4">
            <InviteMemberForm
              onSubmit={async (email, role) => {
                if (!workspaceApi) {
                  return;
                }
                await workspaceApi.inviteMember(email, role);
                setShowInviteForm(false);
                await load();
              }}
              onCancel={() => setShowInviteForm(false)}
            />
          </div>
        )}

        <ul className="space-y-2 text-sm">
          {members.map((member) => (
            <li
              key={member.id}
              className="flex justify-between rounded-lg border border-border px-3 py-2"
            >
              <span>{member.email}</span>
              <span className="text-text-muted">{member.role}</span>
            </li>
          ))}
        </ul>
        {invitations.length > 0 && (
          <div className="mt-6">
            <h3 className="mb-2 text-sm font-semibold text-text">
              Ожидающие приглашения
            </h3>
            <ul className="space-y-3 text-sm">
              {invitations.map((invite) => {
                const url = `${window.location.origin}/invite/${invite.token}`;
                return (
                  <li
                    key={invite.id}
                    className="rounded-lg border border-border px-3 py-2"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-text-muted">
                        {invite.email} · {invite.role}
                      </span>
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          className="text-xs font-medium text-primary hover:underline"
                          onClick={() => void copyInviteLink(invite.token)}
                        >
                          {copiedToken === invite.token
                            ? "Скопировано"
                            : "Копировать ссылку"}
                        </button>
                        <button
                          type="button"
                          className="text-xs font-medium text-secondary hover:underline"
                          onClick={async () => {
                            if (!workspaceApi) {
                              return;
                            }
                            try {
                              await workspaceApi.resendInvitation(invite.id);
                              await load();
                            } catch (err) {
                              setError(
                                parseApiError(err, "Не удалось отправить снова"),
                              );
                            }
                          }}
                        >
                          Отправить снова
                        </button>
                        <button
                          type="button"
                          className="text-xs font-medium text-text-muted hover:text-primary"
                          onClick={async () => {
                            if (!workspaceApi) {
                              return;
                            }
                            try {
                              await workspaceApi.revokeInvitation(invite.id);
                              await load();
                            } catch (err) {
                              setError(
                                parseApiError(err, "Не удалось отозвать приглашение"),
                              );
                            }
                          }}
                        >
                          Отозвать
                        </button>
                      </div>
                    </div>
                    <input
                      readOnly
                      value={url}
                      className="mt-2 w-full rounded border border-border bg-cream px-2 py-1 text-xs text-text"
                      onFocus={(event) => event.currentTarget.select()}
                    />
                  </li>
                );
              })}
            </ul>
          </div>
        )}
      </div>

      {activeWorkspace?.role === "owner" && (
        <div className="max-w-2xl rounded-xl border border-border bg-surface p-6">
          <h2 className="text-lg font-semibold text-text">Мультивалюта workspace</h2>
          <p className="mt-1 text-sm text-text-muted">
            Бюджеты и транзакции хранятся в базовой валюте. Курсы нужны для
            конвертации в валюту отображения.
          </p>
          <div className="mt-4 flex flex-wrap items-end gap-3">
            <label className="text-xs text-text-muted">
              Базовая валюта
              <select
                value={baseCurrencyDraft}
                onChange={(event) => setBaseCurrencyDraft(event.target.value)}
                className="mt-1 block rounded-lg border border-border bg-cream px-3 py-2 text-sm text-text"
              >
                <option value="RUB">RUB</option>
                <option value="USD">USD</option>
                <option value="EUR">EUR</option>
              </select>
            </label>
            <button
              type="button"
              className="rounded-lg border border-border px-3 py-2 text-sm font-medium text-text hover:bg-cream"
              onClick={() => {
                if (!workspaceApi) return;
                void workspaceApi
                  .patchSettings({ currency: baseCurrencyDraft })
                  .then(async (data) => {
                    setWsSettings(data);
                    await load();
                  })
                  .catch((err) =>
                    setError(parseApiError(err, "Не удалось обновить валюту")),
                  );
              }}
            >
              Сохранить базовую
            </button>
          </div>
          <form
            className="mt-4 grid gap-3 sm:grid-cols-[1fr_1fr_1fr_auto]"
            onSubmit={(event) => {
              event.preventDefault();
              if (!workspaceApi || !fxRate.trim()) return;
              void workspaceApi
                .createExchangeRate({
                  currency: fxCurrency,
                  rate_to_base: fxRate.trim(),
                  as_of: fxAsOf,
                })
                .then(async () => {
                  setFxRate("");
                  await load();
                })
                .catch((err) =>
                  setError(parseApiError(err, "Не удалось добавить курс")),
                );
            }}
          >
            <label className="text-xs text-text-muted">
              Валюта
              <select
                value={fxCurrency}
                onChange={(event) => setFxCurrency(event.target.value)}
                className="mt-1 w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm"
              >
                <option value="USD">USD</option>
                <option value="EUR">EUR</option>
                <option value="RUB">RUB</option>
              </select>
            </label>
            <label className="text-xs text-text-muted">
              Курс к базе (1 ед.)
              <input
                required
                value={fxRate}
                onChange={(event) => setFxRate(event.target.value)}
                placeholder="90.5"
                className="mt-1 w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm"
              />
            </label>
            <label className="text-xs text-text-muted">
              На дату
              <input
                type="date"
                value={fxAsOf}
                onChange={(event) => setFxAsOf(event.target.value)}
                className="mt-1 w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm"
              />
            </label>
            <button
              type="submit"
              className="rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-white"
            >
              Добавить
            </button>
          </form>
          <ul className="mt-4 space-y-2 text-sm">
            {(wsSettings?.exchange_rates ?? []).map((row: ExchangeRateRow) => (
              <li
                key={`${row.currency}-${row.as_of ?? "base"}`}
                className="flex items-center justify-between rounded-lg border border-border px-3 py-2"
              >
                <span>
                  {row.currency} = {row.rate_to_base} {wsSettings?.currency}
                  {row.as_of ? ` · ${row.as_of}` : " · база"}
                </span>
                {row.id != null && (
                  <button
                    type="button"
                    className="text-xs text-primary hover:underline"
                    onClick={() => {
                      if (!workspaceApi) return;
                      void workspaceApi
                        .deleteExchangeRate(row.id!)
                        .then(() => load())
                        .catch((err) =>
                          setError(parseApiError(err, "Не удалось удалить курс")),
                        );
                    }}
                  >
                    Удалить
                  </button>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {activeWorkspace?.role === "owner" && (
        <div className="max-w-2xl rounded-xl border border-border bg-surface p-6">
          <h2 className="text-lg font-semibold text-text">API-токены</h2>
          <p className="mt-1 text-sm text-text-muted">
            Токены привязаны к текущему workspace. Значение показывается один раз.
          </p>
          <form
            className="mt-4 flex flex-wrap items-end gap-3"
            onSubmit={async (event) => {
              event.preventDefault();
              if (!workspaceApi || !tokenName.trim()) return;
              try {
                const created = await workspaceApi.createApiToken(
                  tokenName.trim(),
                  tokenCanWrite ? ["read", "write"] : ["read"],
                );
                setRevealedToken(created.token ?? "");
                setTokenName("");
                await load();
              } catch (err) {
                setError(parseApiError(err, "Не удалось создать API-токен"));
              }
            }}
          >
            <label className="flex-1 text-xs text-text-muted">
              Название
              <input
                required
                value={tokenName}
                onChange={(event) => setTokenName(event.target.value)}
                className="mt-1 w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm text-text"
              />
            </label>
            <label className="flex items-center gap-2 pb-2 text-sm text-text">
              <input
                type="checkbox"
                checked={tokenCanWrite}
                onChange={(event) => setTokenCanWrite(event.target.checked)}
              />
              Запись
            </label>
            <button
              type="submit"
              className="rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-white"
            >
              Создать
            </button>
          </form>
          {revealedToken && (
            <input
              readOnly
              value={revealedToken}
              onFocus={(event) => event.currentTarget.select()}
              className="mt-3 w-full rounded border border-secondary bg-cream px-3 py-2 font-mono text-xs text-text"
            />
          )}
          <ul className="mt-4 space-y-2 text-sm">
            {apiTokens.map((token) => (
              <li
                key={token.id}
                className="flex items-center justify-between rounded-lg border border-border px-3 py-2"
              >
                <span>
                  {token.name} · <code>{token.prefix}…</code> · {token.scopes.join(", ")}
                </span>
                {!token.revoked_at && (
                  <button
                    type="button"
                    className="text-xs text-primary hover:underline"
                    onClick={async () => {
                      if (!workspaceApi) return;
                      await workspaceApi.revokeApiToken(token.id);
                      await load();
                    }}
                  >
                    Отозвать
                  </button>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {activeWorkspace?.role === "owner" && (
        <div className="max-w-2xl rounded-xl border border-border bg-surface p-6">
          <h2 className="text-lg font-semibold text-text">Исходящие webhooks</h2>
          <p className="mt-1 text-sm text-text-muted">
            HTTPS-события по рискам и приближающимся дедлайнам, подписанные HMAC-SHA256.
          </p>
          <form
            className="mt-4 grid gap-3 sm:grid-cols-[1fr_2fr_auto]"
            onSubmit={async (event) => {
              event.preventDefault();
              if (!workspaceApi) return;
              try {
                const created = await workspaceApi.createWebhook({
                  name: webhookName,
                  url: webhookUrl,
                  events: [
                    "risk.created",
                    "risk.updated",
                    "risk.deleted",
                    "deadline.upcoming",
                  ],
                });
                setRevealedSecret(created.secret ?? "");
                setWebhookName("");
                setWebhookUrl("");
                await load();
              } catch (err) {
                setError(parseApiError(err, "Не удалось создать webhook"));
              }
            }}
          >
            <input
              required
              placeholder="Название"
              value={webhookName}
              onChange={(event) => setWebhookName(event.target.value)}
              className="rounded-lg border border-border bg-cream px-3 py-2 text-sm text-text"
            />
            <input
              required
              type="url"
              placeholder="https://example.com/webhooks"
              value={webhookUrl}
              onChange={(event) => setWebhookUrl(event.target.value)}
              className="rounded-lg border border-border bg-cream px-3 py-2 text-sm text-text"
            />
            <button
              type="submit"
              className="rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-white"
            >
              Добавить
            </button>
          </form>
          {revealedSecret && (
            <p className="mt-3 rounded border border-secondary bg-cream px-3 py-2 font-mono text-xs text-text">
              Secret: {revealedSecret}
            </p>
          )}
          <ul className="mt-4 space-y-2 text-sm">
            {webhooks.map((webhook) => (
              <li
                key={webhook.id}
                className="flex items-center justify-between gap-3 rounded-lg border border-border px-3 py-2"
              >
                <span className="min-w-0">
                  <strong>{webhook.name}</strong>
                  <span className="ml-2 break-all text-xs text-text-muted">
                    {webhook.url}
                  </span>
                </span>
                <div className="flex shrink-0 items-center gap-2">
                  <button
                    type="button"
                    className="text-xs text-secondary hover:underline"
                    onClick={async () => {
                      if (!workspaceApi) return;
                      setWebhookTestMessage("");
                      try {
                        const result = await workspaceApi.testWebhook(webhook.id);
                        const detail =
                          result.status_code != null
                            ? `HTTP ${result.status_code}`
                            : result.error || result.status;
                        setWebhookTestMessage(
                          `Тест webhook «${webhook.name}»: ${detail}`,
                        );
                      } catch (err) {
                        setWebhookTestMessage(
                          parseApiError(err, "Не удалось отправить тест"),
                        );
                      }
                    }}
                  >
                    Тест
                  </button>
                  <button
                    type="button"
                    className="text-xs text-primary hover:underline"
                    onClick={async () => {
                      if (!workspaceApi) return;
                      await workspaceApi.deleteWebhook(webhook.id);
                      await load();
                    }}
                  >
                    Удалить
                  </button>
                </div>
              </li>
            ))}
          </ul>
          {webhookTestMessage && (
            <p className="mt-3 text-xs text-text-muted">{webhookTestMessage}</p>
          )}
        </div>
      )}
    </div>
  );
}
