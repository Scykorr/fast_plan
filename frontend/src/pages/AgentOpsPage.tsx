import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { parseApiError } from "../api/errors";
import type {
  AgentProfile,
  DeliveryEpic,
  DeliveryOverview,
  DeliverySprint,
  DeliveryTask,
} from "../api/delivery";
import { ErrorMessage } from "../components/ErrorMessage";
import { useDeliveryApi } from "../hooks/useDeliveryApi";
import { useWorkspace } from "../context/WorkspaceContext";

const STATUSES = [
  "draft",
  "ready",
  "assigned",
  "in_progress",
  "blocked",
  "review",
  "qa",
  "done",
  "archived",
] as const;

const ROLES = [
  "documentation",
  "smart_contract",
  "backend",
  "frontend",
  "qa",
  "owner",
  "human",
  "planner",
  "reviewer",
  "observer",
] as const;

const emptyTaskForm = {
  title: "",
  business_outcome: "",
  context: "",
  scope_in: "",
  scope_out: "",
  ready_criterion: "",
  done_criterion: "",
  expected_checks: "",
  result_artifact: "",
  assignee_role: "backend",
  next_role: "qa",
  canon_url: "",
  architecture_url: "",
  planning_doc_url: "",
  acceptance_url: "",
  external_pack_url: "",
  github_repo: "",
  github_branch: "",
  epic: "" as number | "",
  sprint: "" as number | "",
};

type Tab =
  | "overview"
  | "backlog"
  | "task"
  | "agents"
  | "sprints"
  | "epics"
  | "projects";

export function AgentOpsPage() {
  const api = useDeliveryApi();
  const { workspaceEpoch } = useWorkspace();
  const [params, setParams] = useSearchParams();
  const [enabled, setEnabled] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<Tab>(
    (params.get("task") ? "task" : "overview") as Tab,
  );
  const [tasks, setTasks] = useState<DeliveryTask[]>([]);
  const [epics, setEpics] = useState<DeliveryEpic[]>([]);
  const [sprints, setSprints] = useState<DeliverySprint[]>([]);
  const [agents, setAgents] = useState<AgentProfile[]>([]);
  const [overview, setOverview] = useState<DeliveryOverview | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(
    params.get("task") ? Number(params.get("task")) : null,
  );
  const [selected, setSelected] = useState<DeliveryTask | null>(null);
  const [history, setHistory] = useState<{
    status_history: Array<{
      from_status: string;
      to_status: string;
      reason: string;
      created_at: string;
    }>;
    field_history: Array<{
      field: string;
      old_value: string;
      new_value: string;
      created_at: string;
    }>;
    timeline?: Array<{
      kind: string;
      at: string;
      actor_id: number | null;
      summary: string;
      detail: string;
    }>;
  } | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [sprintFilter, setSprintFilter] = useState<number | "">("");
  const [projects, setProjects] = useState<
    Array<{
      project: number;
      project_name: string;
      description: string;
      status: string;
      owner_email: string | null;
      repo_url: string;
      docs_url: string;
    }>
  >([]);
  const [commentBody, setCommentBody] = useState("");
  const [subtaskTitle, setSubtaskTitle] = useState("");
  const [depTaskId, setDepTaskId] = useState("");
  const [projectLinks, setProjectLinks] = useState<
    Record<number, { repo_url: string; docs_url: string }>
  >({});
  const [newProject, setNewProject] = useState({
    name: "",
    description: "",
    repo_url: "",
    docs_url: "",
  });
  const [meaningChanges, setMeaningChanges] = useState<
    import("../api/delivery").MeaningChangeRequest[]
  >([]);
  const [epicTitle, setEpicTitle] = useState("");
  const [sprintName, setSprintName] = useState("");
  const [taskForm, setTaskForm] = useState(emptyTaskForm);
  const [handoff, setHandoff] = useState({
    to_role: "qa",
    done_summary: "",
    left_summary: "",
    branch_or_pr_url: "",
    checks_url: "",
    open_questions: "",
  });
  const [blockerTitle, setBlockerTitle] = useState("");
  const [serviceRole, setServiceRole] = useState("backend");
  const [issuedToken, setIssuedToken] = useState("");
  const [ghSecret, setGhSecret] = useState("");
  const [ghToken, setGhToken] = useState("");
  const [settingsFlags, setSettingsFlags] = useState({
    webhook: false,
    token: false,
  });
  const [newPr, setNewPr] = useState({
    repo: "",
    branch: "",
    pr_number: "",
    pr_url: "",
  });

  const load = useCallback(async () => {
    if (!api) return;
    setLoading(true);
    setError("");
    try {
      const settings = await api.getSettings();
      setEnabled(settings.agent_ops_enabled);
      setSettingsFlags({
        webhook: Boolean(settings.github_webhook_secret_set),
        token: Boolean(settings.github_api_token_set),
      });
      if (!settings.agent_ops_enabled) {
        setTasks([]);
        setEpics([]);
        setSprints([]);
        setAgents([]);
        setOverview(null);
        return;
      }
      const [taskRows, epicRows, sprintRows, agentRows, ov, projectRows] =
        await Promise.all([
          api.listTasks({
            status: statusFilter || undefined,
            role: roleFilter || undefined,
            sprint: sprintFilter === "" ? undefined : sprintFilter,
          }),
          api.listEpics(),
          api.listSprints(),
          api.listAgents(),
          api.overview(),
          api.listProjects(),
        ]);
      setTasks(taskRows);
      setEpics(epicRows);
      setSprints(sprintRows);
      setAgents(agentRows);
      setOverview(ov);
      setProjects(projectRows);
      setProjectLinks(
        Object.fromEntries(
          projectRows.map((p) => [
            p.project,
            { repo_url: p.repo_url || "", docs_url: p.docs_url || "" },
          ]),
        ),
      );
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setLoading(false);
    }
  }, [api, statusFilter, sprintFilter, roleFilter]);

  const loadTask = useCallback(
    async (id: number) => {
      if (!api) return;
      try {
        const [task, hist, meanings] = await Promise.all([
          api.getTask(id),
          api.getHistory(id),
          api.listMeaningChanges(id),
        ]);
        setSelected(task);
        setHistory(hist);
        setMeaningChanges(meanings);
      } catch (err) {
        setError(parseApiError(err));
      }
    },
    [api],
  );

  useEffect(() => {
    void load();
  }, [load, workspaceEpoch]);

  useEffect(() => {
    if (selectedId && enabled) {
      void loadTask(selectedId);
    }
  }, [selectedId, enabled, loadTask]);

  const openTask = (id: number) => {
    setSelectedId(id);
    setTab("task");
    setParams({ task: String(id) });
  };

  const toggleEnabled = async () => {
    if (!api) return;
    try {
      const next = await api.patchSettings({ agent_ops_enabled: !enabled });
      setEnabled(next.agent_ops_enabled);
      setMessage(
        next.agent_ops_enabled
          ? "Agent Ops включён"
          : "Agent Ops выключен",
      );
      await load();
    } catch (err) {
      setError(parseApiError(err));
    }
  };

  const createEpic = async () => {
    if (!api || !epicTitle.trim()) return;
    try {
      await api.createEpic({ title: epicTitle.trim() });
      setEpicTitle("");
      setMessage("Эпик создан");
      await load();
    } catch (err) {
      setError(parseApiError(err));
    }
  };

  const createSprint = async () => {
    if (!api || !sprintName.trim()) return;
    try {
      await api.createSprint({ name: sprintName.trim(), status: "active" });
      setSprintName("");
      setMessage("Спринт создан");
      await load();
    } catch (err) {
      setError(parseApiError(err));
    }
  };

  const createTask = async () => {
    if (!api || !taskForm.title.trim()) return;
    try {
      const created = await api.createTask({
        title: taskForm.title.trim(),
        business_outcome: taskForm.business_outcome,
        context: taskForm.context,
        scope_in: taskForm.scope_in,
        scope_out: taskForm.scope_out,
        ready_criterion: taskForm.ready_criterion,
        done_criterion: taskForm.done_criterion,
        expected_checks: taskForm.expected_checks,
        result_artifact: taskForm.result_artifact,
        assignee_role: taskForm.assignee_role,
        next_role: taskForm.next_role,
        canon_url: taskForm.canon_url,
        architecture_url: taskForm.architecture_url,
        planning_doc_url: taskForm.planning_doc_url,
        acceptance_url: taskForm.acceptance_url,
        external_pack_url: taskForm.external_pack_url,
        github_repo: taskForm.github_repo,
        github_branch: taskForm.github_branch,
        epic: taskForm.epic === "" ? null : taskForm.epic,
        sprint: taskForm.sprint === "" ? null : taskForm.sprint,
      });
      setTaskForm(emptyTaskForm);
      setMessage(`Задача #${created.id} создана`);
      await load();
      openTask(created.id);
    } catch (err) {
      setError(parseApiError(err));
    }
  };

  const makeReady = async (task: DeliveryTask) => {
    if (!api) return;
    try {
      await api.setStatus(task.id, "ready");
      setMessage(`#${task.id} → Ready`);
      await load();
      if (selectedId === task.id) await loadTask(task.id);
    } catch (err) {
      setError(parseApiError(err));
    }
  };

  const claim = async (task: DeliveryTask) => {
    if (!api) return;
    try {
      await api.claimTask(task.id, task.version);
      setMessage(`#${task.id} claimed`);
      await load();
      if (selectedId === task.id) await loadTask(task.id);
    } catch (err) {
      setError(parseApiError(err));
    }
  };

  const submitHandoff = async () => {
    if (!api || !selected) return;
    try {
      await api.createHandoff(selected.id, {
        from_role: selected.assignee_role,
        ...handoff,
      });
      setMessage("Handoff создан");
      setHandoff({
        to_role: "qa",
        done_summary: "",
        left_summary: "",
        branch_or_pr_url: "",
        checks_url: "",
        open_questions: "",
      });
      await load();
      await loadTask(selected.id);
    } catch (err) {
      setError(parseApiError(err));
    }
  };

  const addBlocker = async () => {
    if (!api || !selected || !blockerTitle.trim()) return;
    try {
      await api.createBlocker(selected.id, {
        title: blockerTitle.trim(),
        needs_owner_decision: true,
      });
      setBlockerTitle("");
      setMessage("Блокер отмечен");
      await loadTask(selected.id);
      await load();
    } catch (err) {
      setError(parseApiError(err));
    }
  };

  const provisionAgent = async () => {
    if (!api) return;
    try {
      const row = await api.createServiceAccount({
        role: serviceRole,
        display_name: `${serviceRole} bot`,
      });
      setIssuedToken(row.api_token_raw || "");
      setMessage(`Service account: ${row.service_user_email}`);
      await load();
    } catch (err) {
      setError(parseApiError(err));
    }
  };

  const copyPrSnippet = async () => {
    if (!api || !selected) return;
    try {
      const snip = await api.prSnippet(selected.id);
      await navigator.clipboard.writeText(snip.markdown);
      setMessage("PR snippet скопирован");
    } catch (err) {
      setError(parseApiError(err));
    }
  };

  const attachPr = async () => {
    if (!api || !selected) return;
    try {
      const res = await api.attachPr(selected.id);
      setMessage(
        res.skipped
          ? "Ссылка уже есть в PR"
          : `Ссылка прикреплена к PR${res.pr_url ? `: ${res.pr_url}` : ""}`,
      );
      await loadTask(selected.id);
    } catch (err) {
      setError(parseApiError(err));
    }
  };

  const reviewMeaning = async (
    requestId: number,
    decision: "approve" | "reject",
  ) => {
    if (!api || !selected) return;
    try {
      await api.reviewMeaningChange(selected.id, requestId, { decision });
      setMessage(
        decision === "approve"
          ? `Meaning change #${requestId} approved`
          : `Meaning change #${requestId} rejected`,
      );
      await loadTask(selected.id);
      await load();
    } catch (err) {
      setError(parseApiError(err));
    }
  };

  const createProject = async () => {
    if (!api || !newProject.name.trim()) return;
    try {
      await api.upsertProjectMeta({
        name: newProject.name.trim(),
        description: newProject.description,
        repo_url: newProject.repo_url,
        docs_url: newProject.docs_url,
      });
      setNewProject({ name: "", description: "", repo_url: "", docs_url: "" });
      setMessage("Проект создан");
      await load();
    } catch (err) {
      setError(parseApiError(err));
    }
  };

  const tabs = useMemo(
    () =>
      [
        ["overview", "Обзор"],
        ["backlog", "Backlog"],
        ["task", "Карточка"],
        ["projects", "Проекты"],
        ["agents", "Агенты"],
        ["sprints", "Спринты"],
        ["epics", "Эпики"],
      ] as const,
    [],
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-text">Agent Ops</h1>
          <p className="mt-1 text-sm text-text-muted">
            Операционный слой: эпики, спринты, ЖЦ, handoff, GitHub/docs. Канон
            — во внешних документах.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void toggleEnabled()}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white"
        >
          {enabled ? "Выключить" : "Включить Agent Ops"}
        </button>
      </div>

      {enabled && (
        <section className="grid gap-3 rounded-xl border border-border bg-surface p-4 md:grid-cols-2">
          <div className="space-y-2">
            <h2 className="text-sm font-semibold text-text">GitHub webhook secret</h2>
            <p className="text-xs text-text-muted">
              {settingsFlags.webhook ? "Задан" : "Не задан"} · HMAC X-Hub-Signature-256
            </p>
            <input
              type="password"
              className="w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm"
              placeholder="Новый secret"
              value={ghSecret}
              onChange={(e) => setGhSecret(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <h2 className="text-sm font-semibold text-text">GitHub API token (PAT)</h2>
            <p className="text-xs text-text-muted">
              {settingsFlags.token ? "Задан" : "Не задан"} · auto-attach / Attach to PR
            </p>
            <input
              type="password"
              className="w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm"
              placeholder="ghp_…"
              value={ghToken}
              onChange={(e) => setGhToken(e.target.value)}
            />
          </div>
          <button
            type="button"
            className="rounded-lg border border-border px-3 py-1.5 text-xs md:col-span-2"
            onClick={() => {
              void (async () => {
                if (!api) return;
                try {
                  const body: {
                    github_webhook_secret?: string;
                    github_api_token?: string;
                  } = {};
                  if (ghSecret.trim()) body.github_webhook_secret = ghSecret.trim();
                  if (ghToken.trim()) body.github_api_token = ghToken.trim();
                  if (!Object.keys(body).length) {
                    setMessage("Введите secret и/или token");
                    return;
                  }
                  const next = await api.patchSettings(body);
                  setSettingsFlags({
                    webhook: Boolean(next.github_webhook_secret_set),
                    token: Boolean(next.github_api_token_set),
                  });
                  setGhSecret("");
                  setGhToken("");
                  setMessage("GitHub settings сохранены");
                } catch (err) {
                  setError(parseApiError(err));
                }
              })();
            }}
          >
            Сохранить GitHub settings
          </button>
        </section>
      )}

      <ErrorMessage message={error} />
      {message && (
        <p className="text-sm text-secondary" role="status">
          {message}
        </p>
      )}

      {!enabled && (
        <p className="rounded-xl border border-border bg-surface p-4 text-sm text-text-muted">
          Модуль выключен (`agent_ops_enabled`).
        </p>
      )}

      {enabled && (
        <>
          <div className="flex flex-wrap gap-2">
            {tabs.map(([id, label]) => (
              <button
                key={id}
                type="button"
                onClick={() => setTab(id)}
                className={[
                  "rounded-lg px-3 py-1.5 text-sm font-medium",
                  tab === id
                    ? "bg-primary text-white"
                    : "border border-border bg-surface text-text-muted",
                ].join(" ")}
              >
                {label}
              </button>
            ))}
          </div>

          {loading && <p className="text-sm text-text-muted">Загрузка…</p>}

          {tab === "overview" && overview && (
            <section className="grid gap-4 md:grid-cols-2">
              {(
                [
                  ["Blocked", overview.blocked],
                  ["Stuck in Review", overview.stuck_review],
                  ["Returned from QA", overview.returned_from_qa],
                ] as const
              ).map(([label, rows]) => (
                <div
                  key={label}
                  className="rounded-xl border border-border bg-surface p-4"
                >
                  <h2 className="font-semibold text-text">{label}</h2>
                  <ul className="mt-2 space-y-1 text-sm">
                    {rows.length === 0 && (
                      <li className="text-text-muted">—</li>
                    )}
                    {rows.map((t) => (
                      <li key={t.id}>
                        <button
                          type="button"
                          className="text-primary hover:underline"
                          onClick={() => openTask(t.id)}
                        >
                          #{t.id} {t.title}
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
              <div className="rounded-xl border border-border bg-surface p-4 md:col-span-2">
                <h2 className="font-semibold text-text">Awaiting owner</h2>
                <ul className="mt-2 space-y-1 text-sm">
                  {overview.awaiting_owner.length === 0 && (
                    <li className="text-text-muted">—</li>
                  )}
                  {overview.awaiting_owner.map((b) => (
                    <li key={b.blocker_id}>
                      <button
                        type="button"
                        className="text-primary hover:underline"
                        onClick={() => openTask(b.task_id)}
                      >
                        #{b.task_id} {b.task_title}
                      </button>
                      : {b.title}
                    </li>
                  ))}
                </ul>
              </div>
            </section>
          )}

          {tab === "projects" && (
            <section className="space-y-3">
              <p className="text-sm text-text-muted">
                Проекты workspace + ссылки repo/docs (TZ §5.1).
              </p>
              <div className="space-y-2 rounded-xl border border-border bg-surface p-4">
                <h3 className="font-semibold">Создать проект</h3>
                <input
                  className="w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                  placeholder="Название"
                  value={newProject.name}
                  onChange={(e) =>
                    setNewProject((p) => ({ ...p, name: e.target.value }))
                  }
                />
                <textarea
                  className="w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                  placeholder="Описание"
                  rows={2}
                  value={newProject.description}
                  onChange={(e) =>
                    setNewProject((p) => ({
                      ...p,
                      description: e.target.value,
                    }))
                  }
                />
                <div className="grid gap-2 md:grid-cols-2">
                  <input
                    className="rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                    placeholder="Repo URL"
                    value={newProject.repo_url}
                    onChange={(e) =>
                      setNewProject((p) => ({ ...p, repo_url: e.target.value }))
                    }
                  />
                  <input
                    className="rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                    placeholder="Docs URL"
                    value={newProject.docs_url}
                    onChange={(e) =>
                      setNewProject((p) => ({ ...p, docs_url: e.target.value }))
                    }
                  />
                </div>
                <button
                  type="button"
                  className="rounded-lg bg-primary px-3 py-1.5 text-xs text-white"
                  onClick={() => void createProject()}
                >
                  Создать
                </button>
              </div>
              <ul className="space-y-3">
                {projects.map((p) => (
                  <li
                    key={p.project}
                    className="space-y-2 rounded-xl border border-border bg-surface p-4"
                  >
                    <p className="font-semibold text-text">
                      {p.project_name}{" "}
                      <span className="text-xs font-normal text-text-muted">
                        {p.status}
                        {p.owner_email ? ` · ${p.owner_email}` : ""}
                      </span>
                    </p>
                    <p className="text-xs text-text-muted">
                      {p.description || "—"}
                    </p>
                    <div className="grid gap-2 md:grid-cols-2">
                      <input
                        className="rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                        placeholder="Repo URL"
                        value={projectLinks[p.project]?.repo_url || ""}
                        onChange={(e) =>
                          setProjectLinks((prev) => ({
                            ...prev,
                            [p.project]: {
                              ...(prev[p.project] || {
                                repo_url: "",
                                docs_url: "",
                              }),
                              repo_url: e.target.value,
                            },
                          }))
                        }
                      />
                      <input
                        className="rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                        placeholder="Docs URL"
                        value={projectLinks[p.project]?.docs_url || ""}
                        onChange={(e) =>
                          setProjectLinks((prev) => ({
                            ...prev,
                            [p.project]: {
                              ...(prev[p.project] || {
                                repo_url: "",
                                docs_url: "",
                              }),
                              docs_url: e.target.value,
                            },
                          }))
                        }
                      />
                    </div>
                    <button
                      type="button"
                      className="rounded-lg bg-primary px-3 py-1.5 text-xs text-white"
                      onClick={() => {
                        void (async () => {
                          if (!api) return;
                          try {
                            await api.upsertProjectMeta({
                              project: p.project,
                              ...projectLinks[p.project],
                            });
                            setMessage(`Ссылки проекта #${p.project} сохранены`);
                            await load();
                          } catch (err) {
                            setError(parseApiError(err));
                          }
                        })();
                      }}
                    >
                      Сохранить ссылки
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {tab === "epics" && (
            <section className="space-y-3">
              <div className="flex flex-wrap gap-2">
                <input
                  className="min-w-[12rem] flex-1 rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                  placeholder="Название эпика"
                  value={epicTitle}
                  onChange={(e) => setEpicTitle(e.target.value)}
                />
                <button
                  type="button"
                  onClick={() => void createEpic()}
                  className="rounded-lg bg-primary px-4 py-2 text-sm text-white"
                >
                  Создать эпик
                </button>
              </div>
              <ul className="space-y-2">
                {epics.map((epic) => (
                  <li
                    key={epic.id}
                    className="rounded-xl border border-border bg-surface px-4 py-3"
                  >
                    <p className="font-semibold text-text">{epic.title}</p>
                    <p className="text-xs text-text-muted">
                      {epic.status} · {epic.priority} · tasks:{" "}
                      {epic.task_ids?.length ?? 0}
                    </p>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {tab === "sprints" && (
            <section className="space-y-3">
              <div className="flex flex-wrap gap-2">
                <input
                  className="min-w-[12rem] flex-1 rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                  placeholder="Название спринта"
                  value={sprintName}
                  onChange={(e) => setSprintName(e.target.value)}
                />
                <button
                  type="button"
                  onClick={() => void createSprint()}
                  className="rounded-lg bg-primary px-4 py-2 text-sm text-white"
                >
                  Создать спринт
                </button>
              </div>
              <ul className="space-y-2">
                {sprints.map((sprint) => (
                  <li
                    key={sprint.id}
                    className="rounded-xl border border-border bg-surface px-4 py-3"
                  >
                    <p className="font-semibold text-text">{sprint.name}</p>
                    <p className="text-xs text-text-muted">
                      {sprint.status} · tasks: {sprint.task_count}
                    </p>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {tab === "agents" && (
            <section className="space-y-4">
              <div className="rounded-xl border border-border bg-surface p-4 text-sm space-y-2">
                <h2 className="font-semibold text-text">Onboarding агента</h2>
                <ol className="list-decimal space-y-1 pl-5 text-text-muted">
                  <li>Выберите роль и создайте service account + token (ниже).</li>
                  <li>
                    Сохраните token в secret store агента — он показывается один раз.
                  </li>
                  <li>
                    Заголовок запросов:{" "}
                    <code className="text-xs">Authorization: Token …</code> +{" "}
                    <code className="text-xs">X-Workspace-Id</code>.
                  </li>
                  <li>
                    Типичный цикл: claim → handoff → Owner/Planner approve meaning →
                    Ready-gate.
                  </li>
                  <li>
                    Проверьте ACL роли на карточке агента (effective_actions) и field
                    ACL при PATCH.
                  </li>
                  <li>
                    Полный runbook:{" "}
                    <code className="text-xs">docs/AGENT_OPS.md</code> (очередь,
                    Idempotency-Key, GitHub webhook HMAC).
                  </li>
                </ol>
                <pre className="overflow-x-auto rounded-lg border border-border bg-cream p-2 text-[11px] leading-relaxed text-text-muted">
{`# queue
GET /api/delivery/queue/?role=backend&status=ready
# claim
POST /api/delivery/tasks/{id}/claim/
# handoff
POST /api/delivery/tasks/{id}/handoffs/`}
                </pre>
              </div>
              <div className="flex flex-wrap items-end gap-2 rounded-xl border border-border bg-surface p-4">
                <label className="text-sm">
                  Role
                  <select
                    className="mt-1 block rounded-lg border border-border bg-cream px-3 py-2"
                    value={serviceRole}
                    onChange={(e) => setServiceRole(e.target.value)}
                  >
                    {ROLES.map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                </label>
                <button
                  type="button"
                  onClick={() => void provisionAgent()}
                  className="rounded-lg bg-primary px-4 py-2 text-sm text-white"
                >
                  Создать service account + token
                </button>
              </div>
              {issuedToken && (
                <p className="break-all rounded-lg border border-border bg-cream p-3 text-xs">
                  Token (один раз): {issuedToken}
                </p>
              )}
              <ul className="space-y-2">
                {agents.map((a) => (
                  <li
                    key={a.id}
                    className="rounded-xl border border-border bg-surface px-4 py-3 text-sm"
                  >
                    <p className="font-semibold text-text">
                      {a.display_name || a.user_email} · {a.role}
                    </p>
                    <p className="text-xs text-text-muted">
                      {a.actor_type}
                      {a.is_service_account ? " · service" : ""} · actions:{" "}
                      {(a.effective_actions || []).join(", ")}
                    </p>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {tab === "backlog" && (
            <section className="space-y-4">
              <div className="grid gap-3 rounded-xl border border-border bg-surface p-4 md:grid-cols-2">
                {(
                  [
                    ["title", "Заголовок"],
                    ["business_outcome", "Business outcome"],
                    ["context", "Context"],
                    ["scope_in", "Scope in"],
                    ["scope_out", "Scope out"],
                    ["ready_criterion", "Ready criterion"],
                    ["done_criterion", "Done criterion"],
                    ["expected_checks", "Expected checks"],
                    ["result_artifact", "Result artifact"],
                    ["canon_url", "Canon URL"],
                    ["architecture_url", "Architecture URL"],
                    ["planning_doc_url", "Planning URL"],
                    ["acceptance_url", "Acceptance URL"],
                    ["external_pack_url", "External pack URL"],
                    ["github_repo", "GitHub repo (org/name)"],
                    ["github_branch", "Branch"],
                  ] as const
                ).map(([key, placeholder]) => (
                  <input
                    key={key}
                    className="rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                    placeholder={placeholder}
                    value={taskForm[key]}
                    onChange={(e) =>
                      setTaskForm((p) => ({ ...p, [key]: e.target.value }))
                    }
                  />
                ))}
                <select
                  className="rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                  value={taskForm.assignee_role}
                  onChange={(e) =>
                    setTaskForm((p) => ({
                      ...p,
                      assignee_role: e.target.value,
                    }))
                  }
                >
                  {ROLES.map((role) => (
                    <option key={role} value={role}>
                      role: {role}
                    </option>
                  ))}
                </select>
                <select
                  className="rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                  value={taskForm.next_role}
                  onChange={(e) =>
                    setTaskForm((p) => ({ ...p, next_role: e.target.value }))
                  }
                >
                  {ROLES.map((role) => (
                    <option key={role} value={role}>
                      next: {role}
                    </option>
                  ))}
                </select>
                <select
                  className="rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                  value={taskForm.epic}
                  onChange={(e) =>
                    setTaskForm((p) => ({
                      ...p,
                      epic: e.target.value ? Number(e.target.value) : "",
                    }))
                  }
                >
                  <option value="">Без эпика</option>
                  {epics.map((epic) => (
                    <option key={epic.id} value={epic.id}>
                      {epic.title}
                    </option>
                  ))}
                </select>
                <select
                  className="rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                  value={taskForm.sprint}
                  onChange={(e) =>
                    setTaskForm((p) => ({
                      ...p,
                      sprint: e.target.value ? Number(e.target.value) : "",
                    }))
                  }
                >
                  <option value="">Без спринта</option>
                  {sprints.map((sprint) => (
                    <option key={sprint.id} value={sprint.id}>
                      {sprint.name}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => void createTask()}
                  className="rounded-lg bg-primary px-4 py-2 text-sm text-white md:col-span-2"
                >
                  Создать задачу (draft)
                </button>
              </div>

              <div className="flex flex-wrap gap-2">
                <select
                  className="rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                >
                  <option value="">Все статусы</option>
                  {STATUSES.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
                <select
                  className="rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                  value={roleFilter}
                  onChange={(e) => setRoleFilter(e.target.value)}
                >
                  <option value="">Все роли</option>
                  {ROLES.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
                <select
                  className="rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                  value={sprintFilter}
                  onChange={(e) =>
                    setSprintFilter(
                      e.target.value ? Number(e.target.value) : "",
                    )
                  }
                >
                  <option value="">Все спринты</option>
                  {sprints.map((sprint) => (
                    <option key={sprint.id} value={sprint.id}>
                      {sprint.name}
                    </option>
                  ))}
                </select>
              </div>

              <ul className="space-y-2">
                {tasks.map((task) => (
                  <li
                    key={task.id}
                    className="rounded-xl border border-border bg-surface p-4"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <button
                        type="button"
                        className="text-left"
                        onClick={() => openTask(task.id)}
                      >
                        <p className="font-semibold text-text hover:underline">
                          {task.title}
                        </p>
                        <p className="text-xs text-text-muted">
                          #{task.id} · {task.status} · {task.assignee_role || "—"}
                          {task.ready_missing?.length
                            ? ` · missing: ${task.ready_missing.join(", ")}`
                            : ""}
                        </p>
                      </button>
                      <div className="flex flex-wrap gap-2">
                        {task.status === "draft" && (
                          <button
                            type="button"
                            onClick={() => void makeReady(task)}
                            className="rounded-lg border border-border px-3 py-1.5 text-xs"
                          >
                            → Ready
                          </button>
                        )}
                        {(task.status === "ready" ||
                          task.status === "assigned") && (
                          <button
                            type="button"
                            onClick={() => void claim(task)}
                            className="rounded-lg bg-primary px-3 py-1.5 text-xs text-white"
                          >
                            Claim
                          </button>
                        )}
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {tab === "task" && (
            <section className="space-y-4">
              {!selected && (
                <p className="text-sm text-text-muted">
                  Выберите задачу в Backlog.
                </p>
              )}
              {selected && (
                <>
                  <div className="rounded-xl border border-border bg-surface p-4">
                    <h2 className="text-xl font-semibold text-text">
                      #{selected.id} {selected.title}
                    </h2>
                    <p className="mt-1 text-sm text-text-muted">
                      {selected.status} · role {selected.assignee_role || "—"} ·
                      next {selected.next_role || "—"} · v{selected.version}
                    </p>
                    <dl className="mt-3 grid gap-2 text-sm md:grid-cols-2">
                      <div>
                        <dt className="text-text-muted">Outcome</dt>
                        <dd>{selected.business_outcome || "—"}</dd>
                      </div>
                      <div>
                        <dt className="text-text-muted">Context</dt>
                        <dd>{selected.context || "—"}</dd>
                      </div>
                      <div>
                        <dt className="text-text-muted">Scope in / out</dt>
                        <dd>
                          {selected.scope_in || "—"} / {selected.scope_out || "—"}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-text-muted">DoR / DoD</dt>
                        <dd>
                          {selected.ready_criterion || "—"} /{" "}
                          {selected.done_criterion || "—"}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-text-muted">Docs</dt>
                        <dd className="break-all text-xs">
                          {[
                            selected.canon_url,
                            selected.architecture_url,
                            selected.planning_doc_url,
                            selected.acceptance_url,
                          ]
                            .filter(Boolean)
                            .join(" · ") || "—"}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-text-muted">GitHub</dt>
                        <dd className="text-xs">
                          {selected.github_repo || "—"}{" "}
                          {selected.github_pr_number
                            ? `PR #${selected.github_pr_number} (${selected.github_pr_state})`
                            : ""}
                          {selected.github_checks_status
                            ? ` · checks ${selected.github_checks_status}`
                            : ""}
                          {selected.github_pr_url && (
                            <>
                              {" "}
                              <a
                                className="text-primary hover:underline"
                                href={selected.github_pr_url}
                                target="_blank"
                                rel="noreferrer"
                              >
                                open
                              </a>
                            </>
                          )}
                        </dd>
                      </div>
                    </dl>
                    {(selected.github_links || []).length > 0 && (
                      <div className="mt-3 space-y-1 text-xs">
                        <p className="font-semibold">Linked PRs</p>
                        <ul className="space-y-1">
                          {(selected.github_links || []).map((l) => (
                            <li key={l.id}>
                              {l.is_primary ? "★ " : ""}
                              {l.repo}
                              {l.pr_number ? ` #${l.pr_number}` : ` ${l.branch}`}
                              {l.checks_status
                                ? ` · checks ${l.checks_status}`
                                : ""}
                              {l.attached_to_pr ? " · attached" : ""}
                              {l.pr_url && (
                                <>
                                  {" "}
                                  <a
                                    className="text-primary hover:underline"
                                    href={l.pr_url}
                                    target="_blank"
                                    rel="noreferrer"
                                  >
                                    open
                                  </a>
                                </>
                              )}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    <div className="mt-2 grid gap-2 md:grid-cols-4">
                      <input
                        className="rounded-lg border border-border bg-cream px-2 py-1 text-xs"
                        placeholder="repo"
                        value={newPr.repo}
                        onChange={(e) =>
                          setNewPr((p) => ({ ...p, repo: e.target.value }))
                        }
                      />
                      <input
                        className="rounded-lg border border-border bg-cream px-2 py-1 text-xs"
                        placeholder="branch"
                        value={newPr.branch}
                        onChange={(e) =>
                          setNewPr((p) => ({ ...p, branch: e.target.value }))
                        }
                      />
                      <input
                        className="rounded-lg border border-border bg-cream px-2 py-1 text-xs"
                        placeholder="PR #"
                        value={newPr.pr_number}
                        onChange={(e) =>
                          setNewPr((p) => ({ ...p, pr_number: e.target.value }))
                        }
                      />
                      <button
                        type="button"
                        className="rounded-lg border border-border px-2 py-1 text-xs"
                        onClick={() => {
                          void (async () => {
                            if (!api || !selected) return;
                            try {
                              await api.addGitHubLink(selected.id, {
                                repo: newPr.repo || selected.github_repo,
                                branch: newPr.branch,
                                pr_number: newPr.pr_number
                                  ? Number(newPr.pr_number)
                                  : null,
                                is_primary: true,
                              });
                              setNewPr({
                                repo: "",
                                branch: "",
                                pr_number: "",
                                pr_url: "",
                              });
                              await loadTask(selected.id);
                            } catch (err) {
                              setError(parseApiError(err));
                            }
                          })();
                        }}
                      >
                        Add PR link
                      </button>
                    </div>
                    {(selected.github_reviews || []).length > 0 && (
                      <div className="mt-3 space-y-2">
                        <p className="text-sm font-semibold">GitHub reviews</p>
                        <ul className="space-y-2 text-xs">
                          {(selected.github_reviews || []).map((r) => (
                            <li
                              key={r.id}
                              className="rounded-lg border border-border bg-cream p-2"
                            >
                              <span className="font-medium">
                                [{r.state}] {r.author_login || "—"}
                              </span>
                              {r.is_resolved ? " · resolved" : " · open"}
                              <p className="mt-1 whitespace-pre-wrap text-text-muted">
                                {r.body || "—"}
                              </p>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {selected.github_review_notes && (
                      <pre className="mt-3 overflow-x-auto rounded bg-cream p-2 text-xs">
                        {selected.github_review_notes}
                      </pre>
                    )}
                    <div className="mt-3 flex flex-wrap gap-2">
                      {selected.status === "draft" && (
                        <button
                          type="button"
                          onClick={() => void makeReady(selected)}
                          className="rounded-lg border border-border px-3 py-1.5 text-xs"
                        >
                          → Ready
                        </button>
                      )}
                      {(selected.status === "ready" ||
                        selected.status === "assigned") && (
                        <button
                          type="button"
                          onClick={() => void claim(selected)}
                          className="rounded-lg bg-primary px-3 py-1.5 text-xs text-white"
                        >
                          Claim
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => void copyPrSnippet()}
                        className="rounded-lg border border-border px-3 py-1.5 text-xs"
                      >
                        Copy PR snippet
                      </button>
                      <button
                        type="button"
                        onClick={() => void attachPr()}
                        className="rounded-lg border border-border px-3 py-1.5 text-xs"
                      >
                        Attach link to PR
                      </button>
                    </div>
                  </div>

                  {meaningChanges.some((m) => m.status === "pending") && (
                    <div className="space-y-2 rounded-xl border border-amber-300 bg-surface p-4">
                      <h3 className="font-semibold">Meaning change requests</h3>
                      <ul className="space-y-2 text-sm">
                        {meaningChanges
                          .filter((m) => m.status === "pending")
                          .map((m) => (
                            <li
                              key={m.id}
                              className="flex flex-wrap items-center justify-between gap-2"
                            >
                              <span>
                                #{m.id}:{" "}
                                {Object.entries(m.proposed_fields)
                                  .map(([k, v]) => `${k}=${String(v)}`)
                                  .join(", ")}
                              </span>
                              <span className="flex gap-2">
                                <button
                                  type="button"
                                  className="rounded-lg bg-primary px-2 py-1 text-xs text-white"
                                  onClick={() =>
                                    void reviewMeaning(m.id, "approve")
                                  }
                                >
                                  Approve
                                </button>
                                <button
                                  type="button"
                                  className="rounded-lg border border-border px-2 py-1 text-xs"
                                  onClick={() =>
                                    void reviewMeaning(m.id, "reject")
                                  }
                                >
                                  Reject
                                </button>
                              </span>
                            </li>
                          ))}
                      </ul>
                    </div>
                  )}

                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2 rounded-xl border border-border bg-surface p-4">
                      <h3 className="font-semibold">Handoff</h3>
                      <select
                        className="w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                        value={handoff.to_role}
                        onChange={(e) =>
                          setHandoff((p) => ({ ...p, to_role: e.target.value }))
                        }
                      >
                        {ROLES.map((r) => (
                          <option key={r} value={r}>
                            → {r}
                          </option>
                        ))}
                      </select>
                      {(
                        [
                          ["done_summary", "Done summary"],
                          ["left_summary", "Left"],
                          ["branch_or_pr_url", "Branch/PR URL"],
                          ["checks_url", "Checks URL"],
                          ["open_questions", "Open questions"],
                        ] as const
                      ).map(([key, ph]) => (
                        <input
                          key={key}
                          className="w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                          placeholder={ph}
                          value={handoff[key]}
                          onChange={(e) =>
                            setHandoff((p) => ({ ...p, [key]: e.target.value }))
                          }
                        />
                      ))}
                      <button
                        type="button"
                        onClick={() => void submitHandoff()}
                        className="rounded-lg bg-primary px-3 py-2 text-sm text-white"
                      >
                        Отправить handoff
                      </button>
                    </div>

                    <div className="space-y-2 rounded-xl border border-border bg-surface p-4">
                      <h3 className="font-semibold">Блокер</h3>
                      <input
                        className="w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                        placeholder="Заголовок блокера"
                        value={blockerTitle}
                        onChange={(e) => setBlockerTitle(e.target.value)}
                      />
                      <button
                        type="button"
                        onClick={() => void addBlocker()}
                        className="rounded-lg border border-border px-3 py-2 text-sm"
                      >
                        Отметить блокер
                      </button>
                      <ul className="space-y-2 text-sm">
                        {(selected.blockers || []).map((b) => (
                          <li
                            key={b.id}
                            className="flex flex-wrap items-center gap-2"
                          >
                            <span>
                              #{b.id} {b.title}{" "}
                              {b.is_open ? "(open)" : "(closed)"}
                            </span>
                            {b.is_open && (
                              <>
                                <button
                                  type="button"
                                  className="text-xs text-primary hover:underline"
                                  onClick={() => {
                                    void (async () => {
                                      if (!api) return;
                                      try {
                                        await api.resolveBlocker(
                                          selected.id,
                                          b.id,
                                          "resolved in UI",
                                        );
                                        await loadTask(selected.id);
                                        await load();
                                      } catch (err) {
                                        setError(parseApiError(err));
                                      }
                                    })();
                                  }}
                                >
                                  Resolve
                                </button>
                                <button
                                  type="button"
                                  className="text-xs text-primary hover:underline"
                                  onClick={() => {
                                    void (async () => {
                                      if (!api) return;
                                      try {
                                        await api.cancelBlocker(
                                          selected.id,
                                          b.id,
                                          "cancelled in UI",
                                        );
                                        await loadTask(selected.id);
                                        await load();
                                      } catch (err) {
                                        setError(parseApiError(err));
                                      }
                                    })();
                                  }}
                                >
                                  Cancel
                                </button>
                              </>
                            )}
                          </li>
                        ))}
                      </ul>
                      <h3 className="pt-2 font-semibold">Dependencies</h3>
                      <div className="flex gap-2">
                        <input
                          className="flex-1 rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                          placeholder="depends on task id"
                          value={depTaskId}
                          onChange={(e) => setDepTaskId(e.target.value)}
                        />
                        <button
                          type="button"
                          className="rounded-lg border border-border px-3 py-2 text-sm"
                          onClick={() => {
                            void (async () => {
                              if (!api || !selected || !depTaskId) return;
                              try {
                                await api.addDependency(
                                  selected.id,
                                  Number(depTaskId),
                                );
                                setDepTaskId("");
                                await loadTask(selected.id);
                              } catch (err) {
                                setError(parseApiError(err));
                              }
                            })();
                          }}
                        >
                          Add
                        </button>
                      </div>
                      <ul className="text-sm">
                        {(selected.dependencies || []).length === 0 && (
                          <li className="text-text-muted">—</li>
                        )}
                        {(selected.dependencies || []).map((d) => (
                          <li key={d.id}>
                            depends on #{d.depends_on} {d.depends_on_title} (
                            {d.depends_on_status})
                          </li>
                        ))}
                      </ul>
                      <h3 className="pt-2 font-semibold">Subtasks</h3>
                      <div className="flex gap-2">
                        <input
                          className="flex-1 rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                          placeholder="Subtask title"
                          value={subtaskTitle}
                          onChange={(e) => setSubtaskTitle(e.target.value)}
                        />
                        <button
                          type="button"
                          className="rounded-lg border border-border px-3 py-2 text-sm"
                          onClick={() => {
                            void (async () => {
                              if (!api || !selected || !subtaskTitle.trim())
                                return;
                              try {
                                await api.createSubtask(selected.id, {
                                  title: subtaskTitle.trim(),
                                });
                                setSubtaskTitle("");
                                await loadTask(selected.id);
                              } catch (err) {
                                setError(parseApiError(err));
                              }
                            })();
                          }}
                        >
                          Add
                        </button>
                      </div>
                      <h3 className="pt-2 font-semibold">Comments</h3>
                      <div className="flex gap-2">
                        <input
                          className="flex-1 rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                          placeholder="Comment"
                          value={commentBody}
                          onChange={(e) => setCommentBody(e.target.value)}
                        />
                        <button
                          type="button"
                          className="rounded-lg border border-border px-3 py-2 text-sm"
                          onClick={() => {
                            void (async () => {
                              if (!api || !selected || !commentBody.trim())
                                return;
                              try {
                                await api.addComment(selected.id, {
                                  body: commentBody.trim(),
                                });
                                setCommentBody("");
                                await loadTask(selected.id);
                              } catch (err) {
                                setError(parseApiError(err));
                              }
                            })();
                          }}
                        >
                          Send
                        </button>
                      </div>
                    </div>
                  </div>

                  {history && (
                    <div className="grid gap-4 md:grid-cols-2">
                      <div className="rounded-xl border border-border bg-surface p-4">
                        <h3 className="font-semibold">Unified timeline</h3>
                        <ul className="mt-2 max-h-64 space-y-1 overflow-y-auto text-xs">
                          {(history.timeline || []).map((h, i) => (
                            <li key={`${h.at}-${i}`}>
                              [{h.kind}] {h.summary}
                            </li>
                          ))}
                        </ul>
                      </div>
                      <div className="rounded-xl border border-border bg-surface p-4">
                        <h3 className="font-semibold">Status history</h3>
                        <ul className="mt-2 max-h-48 space-y-1 overflow-y-auto text-xs">
                          {history.status_history.map((h, i) => (
                            <li key={`${h.created_at}-${i}`}>
                              {h.from_status || "∅"} → {h.to_status}
                              {h.reason ? ` (${h.reason})` : ""}
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  )}
                </>
              )}
            </section>
          )}
        </>
      )}
    </div>
  );
}
