import { useCallback, useEffect, useState } from "react";

import { parseApiError } from "../api/errors";
import type { WorkspaceInvitation, WorkspaceMember } from "../api/workspace";
import { ErrorMessage } from "../components/ErrorMessage";
import { InviteMemberForm } from "../components/workspace/InviteMemberForm";
import { useAuth } from "../context/AuthContext";
import { useWorkspace } from "../context/WorkspaceContext";
import { useWorkspaceApi } from "../hooks/useWorkspaceApi";

export function SettingsPage() {
  const { user } = useAuth();
  const { activeWorkspace, workspaces, switchWorkspace, workspaceEpoch } =
    useWorkspace();
  const workspaceApi = useWorkspaceApi();
  const [members, setMembers] = useState<WorkspaceMember[]>([]);
  const [invitations, setInvitations] = useState<WorkspaceInvitation[]>([]);
  const [error, setError] = useState("");
  const [copiedToken, setCopiedToken] = useState<string | null>(null);
  const [showInviteForm, setShowInviteForm] = useState(false);

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
                      <button
                        type="button"
                        className="text-xs font-medium text-primary hover:underline"
                        onClick={() => void copyInviteLink(invite.token)}
                      >
                        {copiedToken === invite.token
                          ? "Скопировано"
                          : "Копировать ссылку"}
                      </button>
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
