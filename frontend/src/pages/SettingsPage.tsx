import { useCallback, useEffect, useState, type FormEvent } from "react";

import { api } from "../api/client";
import { parseApiError } from "../api/errors";
import type { WorkspaceInvitation, WorkspaceMember } from "../api/workspace";
import { ErrorMessage } from "../components/ErrorMessage";
import { InviteMemberForm } from "../components/workspace/InviteMemberForm";
import { useAuth } from "../context/AuthContext";
import { useWorkspace } from "../context/WorkspaceContext";
import { useWorkspaceApi } from "../hooks/useWorkspaceApi";

export function SettingsPage() {
  const { user, logout } = useAuth();
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
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить workspace"));
    }
  }, [workspaceApi]);

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

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-text">Настройки</h1>
        <p className="mt-1 text-sm text-text-muted">Профиль и workspace</p>
      </div>

      {error && <ErrorMessage message={error} onDismiss={() => setError("")} />}

      <div className="max-w-lg rounded-xl border border-border bg-surface p-6">
        <h2 className="mb-4 text-lg font-semibold text-text">Профиль</h2>
        <dl className="space-y-4 text-sm">
          <div>
            <dt className="text-text-muted">Email</dt>
            <dd className="mt-1 font-medium">{user?.email}</dd>
          </div>
          <div>
            <dt className="text-text-muted">Имя пользователя</dt>
            <dd className="mt-1 font-medium">{user?.username}</dd>
          </div>
        </dl>

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
    </div>
  );
}
