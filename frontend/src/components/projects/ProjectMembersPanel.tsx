import { useCallback, useEffect, useMemo, useState } from "react";

import { parseApiError } from "../../api/errors";
import type { ProjectMember } from "../../api/projects";
import { ErrorMessage } from "../ErrorMessage";
import { useProjectsApi } from "../../hooks/useProjectsApi";
import { useWorkspaceApi } from "../../hooks/useWorkspaceApi";
import { useWorkspace } from "../../context/WorkspaceContext";

const ROLE_LABELS: Record<ProjectMember["role"], string> = {
  manager: "Менеджер",
  contributor: "Участник",
  viewer: "Наблюдатель",
};

type Props = {
  projectId: number;
};

export function ProjectMembersPanel({ projectId }: Props) {
  const projectsApi = useProjectsApi();
  const workspaceApi = useWorkspaceApi();
  const { activeWorkspace } = useWorkspace();
  const canEdit =
    activeWorkspace?.role === "owner" || activeWorkspace?.role === "editor";

  const [members, setMembers] = useState<ProjectMember[]>([]);
  const [workspaceMembers, setWorkspaceMembers] = useState<
    Array<{ user_id: number; email: string; username: string }>
  >([]);
  const [userId, setUserId] = useState<number | "">("");
  const [role, setRole] = useState<ProjectMember["role"]>("contributor");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    if (!projectsApi) {
      return;
    }
    try {
      setMembers(await projectsApi.getProjectMembers(projectId));
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить участников проекта"));
    }
  }, [projectsApi, projectId]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!workspaceApi) {
      return;
    }
    void workspaceApi
      .getMembers()
      .then((items) =>
        setWorkspaceMembers(
          items.map((item) => ({
            user_id: item.user_id,
            email: item.email,
            username: item.username,
          })),
        ),
      )
      .catch(() => undefined);
  }, [workspaceApi]);

  const assignableUsers = useMemo(() => {
    const assigned = new Set(members.map((member) => member.user_id));
    return workspaceMembers.filter((member) => !assigned.has(member.user_id));
  }, [members, workspaceMembers]);

  const handleAdd = async () => {
    if (!projectsApi || userId === "") {
      return;
    }
    setSaving(true);
    setError("");
    try {
      await projectsApi.addProjectMember(projectId, {
        user_id: userId,
        role,
      });
      setUserId("");
      setRole("contributor");
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось добавить участника"));
    } finally {
      setSaving(false);
    }
  };

  const handleRoleChange = async (
    member: ProjectMember,
    nextRole: ProjectMember["role"],
  ) => {
    if (!projectsApi || member.role === nextRole) {
      return;
    }
    try {
      await projectsApi.addProjectMember(projectId, {
        user_id: member.user_id,
        role: nextRole,
      });
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось обновить роль"));
    }
  };

  const handleRemove = async (memberId: number) => {
    if (!projectsApi) {
      return;
    }
    try {
      await projectsApi.removeProjectMember(projectId, memberId);
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось удалить участника"));
    }
  };

  return (
    <div className="rounded-xl border border-border bg-surface p-5">
      <h2 className="text-lg font-semibold text-text">Участники проекта</h2>
      <p className="mt-1 text-sm text-text-muted">
        Роли manager / contributor / viewer поверх workspace RBAC
      </p>
      {error && (
        <div className="mt-3">
          <ErrorMessage message={error} onDismiss={() => setError("")} />
        </div>
      )}
      {canEdit && (
        <div className="mt-4 flex flex-wrap items-end gap-2">
          <label className="min-w-[200px] flex-1 text-xs text-text-muted">
            Участник workspace
            <select
              value={userId}
              onChange={(event) =>
                setUserId(event.target.value ? Number(event.target.value) : "")
              }
              className="mt-1 w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm text-text"
            >
              <option value="">Выберите...</option>
              {assignableUsers.map((member) => (
                <option key={member.user_id} value={member.user_id}>
                  {member.username || member.email}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs text-text-muted">
            Роль
            <select
              value={role}
              onChange={(event) =>
                setRole(event.target.value as ProjectMember["role"])
              }
              className="mt-1 block rounded-lg border border-border bg-cream px-3 py-2 text-sm text-text"
            >
              <option value="manager">Менеджер</option>
              <option value="contributor">Участник</option>
              <option value="viewer">Наблюдатель</option>
            </select>
          </label>
          <button
            type="button"
            disabled={saving || userId === ""}
            onClick={() => void handleAdd()}
            className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50"
          >
            {saving ? "Сохранение..." : "Добавить"}
          </button>
        </div>
      )}
      {members.length === 0 ? (
        <p className="mt-4 text-sm text-text-muted">
          Явных ролей на проекте пока нет — действует workspace RBAC
        </p>
      ) : (
        <ul className="mt-4 space-y-2">
          {members.map((member) => (
            <li
              key={member.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-cream px-3 py-2 text-sm"
            >
              <div>
                <p className="font-medium text-text">
                  {member.username || member.email}
                </p>
                <p className="text-xs text-text-muted">{member.email}</p>
              </div>
              <div className="flex items-center gap-2">
                {canEdit ? (
                  <select
                    value={member.role}
                    onChange={(event) =>
                      void handleRoleChange(
                        member,
                        event.target.value as ProjectMember["role"],
                      )
                    }
                    className="rounded border border-border bg-surface px-2 py-1 text-xs"
                  >
                    <option value="manager">Менеджер</option>
                    <option value="contributor">Участник</option>
                    <option value="viewer">Наблюдатель</option>
                  </select>
                ) : (
                  <span className="text-xs text-text-muted">
                    {ROLE_LABELS[member.role]}
                  </span>
                )}
                {canEdit && (
                  <button
                    type="button"
                    onClick={() => void handleRemove(member.id)}
                    className="text-xs text-text-muted hover:underline"
                  >
                    Удалить
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
