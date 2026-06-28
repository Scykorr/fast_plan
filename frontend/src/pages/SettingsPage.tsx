import { useCallback, useEffect, useState } from "react";

import { parseApiError } from "../api/errors";
import type { WorkspaceInvitation, WorkspaceMember } from "../api/workspace";
import { ErrorMessage } from "../components/ErrorMessage";
import { useAuth } from "../context/AuthContext";
import { useWorkspaceApi } from "../hooks/useWorkspaceApi";

export function SettingsPage() {
  const { user } = useAuth();
  const workspaceApi = useWorkspaceApi();
  const [members, setMembers] = useState<WorkspaceMember[]>([]);
  const [invitations, setInvitations] = useState<WorkspaceInvitation[]>([]);
  const [error, setError] = useState("");

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
  }, [load]);

  const handleInvite = async () => {
    if (!workspaceApi) {
      return;
    }
    const email = window.prompt("Email участника");
    if (!email?.trim()) {
      return;
    }
    try {
      await workspaceApi.inviteMember(email.trim());
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось отправить приглашение"));
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
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-text">Участники workspace</h2>
          <button
            type="button"
            onClick={() => void handleInvite()}
            className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white hover:bg-primary-hover"
          >
            Пригласить
          </button>
        </div>
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
            <ul className="space-y-2 text-sm text-text-muted">
              {invitations.map((invite) => (
                <li key={invite.id}>
                  {invite.email} · {invite.role}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
