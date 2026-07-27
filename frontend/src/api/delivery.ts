import { request } from "./client";

export type DeliverySettings = {
  agent_ops_enabled: boolean;
  updated_at: string;
};

export type AgentProfile = {
  id: number;
  user: number;
  user_email: string;
  role: string;
  actor_type: "human" | "agent";
  display_name: string;
  is_active: boolean;
  is_service_account: boolean;
  allowed_actions: string[];
  allowed_project_ids: number[];
  effective_actions: string[];
  api_token: number | null;
  created_at: string;
  api_token_raw?: string;
  service_user_email?: string;
};

export type DeliveryEpic = {
  id: number;
  project: number | null;
  title: string;
  description: string;
  goal: string;
  owner: number | null;
  priority: string;
  status: string;
  planning_doc_url: string;
  task_ids: number[];
  created_at: string;
  updated_at: string;
};

export type DeliverySprint = {
  id: number;
  project: number | null;
  name: string;
  goal: string;
  starts_on: string | null;
  ends_on: string | null;
  capacity: number;
  status: string;
  task_count: number;
  task_ids: number[];
  created_at: string;
  updated_at: string;
};

export type DeliveryTask = {
  id: number;
  project: number | null;
  epic: number | null;
  sprint: number | null;
  title: string;
  description: string;
  business_outcome: string;
  context: string;
  task_type: string;
  priority: string;
  status: string;
  assignee_role: string;
  assignee: number | null;
  assignee_email: string | null;
  created_by: number | null;
  ready_criterion: string;
  done_criterion: string;
  scope_in: string;
  scope_out: string;
  expected_checks: string;
  result_artifact: string;
  next_role: string;
  canon_url: string;
  architecture_url: string;
  planning_doc_url: string;
  acceptance_url: string;
  external_pack_url: string;
  github_repo: string;
  github_branch: string;
  github_commit: string;
  github_pr_url: string;
  github_pr_number: number | null;
  github_pr_state: string;
  github_checks_url: string;
  github_checks_status: string;
  github_review_notes: string;
  version: number;
  open_blockers_count: number;
  ready_missing: string[];
  dependencies?: Array<{
    id: number;
    depends_on: number;
    depends_on_title: string;
    depends_on_status: string;
  }>;
  blockers?: Array<{
    id: number;
    title: string;
    is_open: boolean;
    needs_owner_decision: boolean;
  }>;
  handoffs?: Array<{
    id: number;
    from_role: string;
    to_role: string;
    done_summary: string;
  }>;
  created_at: string;
  updated_at: string;
};

export type DeliveryOverview = {
  agent_ops_enabled: boolean;
  blocked: DeliveryTask[];
  stuck_review: DeliveryTask[];
  awaiting_owner: Array<{
    blocker_id: number;
    title: string;
    task_id: number;
    task_title: string;
  }>;
  returned_from_qa: DeliveryTask[];
};

export type DeliveryTaskWrite = Partial<{
  project: number | null;
  epic: number | null;
  sprint: number | null;
  title: string;
  description: string;
  business_outcome: string;
  context: string;
  task_type: string;
  priority: string;
  assignee_role: string;
  assignee: number | null;
  ready_criterion: string;
  done_criterion: string;
  scope_in: string;
  scope_out: string;
  expected_checks: string;
  result_artifact: string;
  next_role: string;
  canon_url: string;
  architecture_url: string;
  planning_doc_url: string;
  acceptance_url: string;
  external_pack_url: string;
  github_repo: string;
  github_branch: string;
  github_commit: string;
  github_pr_url: string;
  github_pr_number: number | null;
  github_pr_state: string;
  github_checks_url: string;
  github_checks_status: string;
  github_review_notes: string;
  confirm_meaning_change?: boolean;
}>;

function qs(params?: Record<string, string | number | boolean | undefined>) {
  if (!params) return "";
  const entries = Object.entries(params).filter(
    ([, v]) => v !== undefined && v !== "",
  );
  if (!entries.length) return "";
  return `?${new URLSearchParams(
    entries.map(([k, v]) => [k, String(v)]),
  ).toString()}`;
}

export function createDeliveryApi() {
  return {
    getSettings: () => request<DeliverySettings>("/delivery/settings/"),
    patchSettings: (data: { agent_ops_enabled: boolean }) =>
      request<DeliverySettings>("/delivery/settings/", {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    overview: () => request<DeliveryOverview>("/delivery/overview/"),
    listAgents: () => request<AgentProfile[]>("/delivery/agents/"),
    createAgent: (data: {
      user: number;
      role: string;
      actor_type?: string;
      display_name?: string;
    }) =>
      request<AgentProfile>("/delivery/agents/", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    createServiceAccount: (data: {
      role: string;
      display_name?: string;
      allowed_actions?: string[];
    }) =>
      request<AgentProfile>("/delivery/agents/service-accounts/", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    listEpics: () => request<DeliveryEpic[]>("/delivery/epics/"),
    createEpic: (data: Partial<DeliveryEpic> & { title: string }) =>
      request<DeliveryEpic>("/delivery/epics/", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    listSprints: () => request<DeliverySprint[]>("/delivery/sprints/"),
    createSprint: (data: Partial<DeliverySprint> & { name: string }) =>
      request<DeliverySprint>("/delivery/sprints/", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    listTasks: (params?: {
      status?: string;
      role?: string;
      sprint?: number;
      epic?: number;
      ready?: boolean;
      mine?: boolean;
    }) => request<DeliveryTask[]>(`/delivery/tasks/${qs(params)}`),
    createTask: (data: DeliveryTaskWrite & { title: string }) =>
      request<DeliveryTask>("/delivery/tasks/", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    getTask: (id: number) => request<DeliveryTask>(`/delivery/tasks/${id}/`),
    patchTask: (id: number, data: DeliveryTaskWrite) =>
      request<DeliveryTask>(`/delivery/tasks/${id}/`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    setStatus: (id: number, status: string, reason?: string) =>
      request<DeliveryTask>(`/delivery/tasks/${id}/status/`, {
        method: "POST",
        body: JSON.stringify({ status, reason: reason || "" }),
      }),
    claimTask: (id: number, version?: number) =>
      request<DeliveryTask>(`/delivery/tasks/${id}/claim/`, {
        method: "POST",
        body: JSON.stringify(version != null ? { version } : {}),
      }),
    createBlocker: (
      taskId: number,
      data: { title: string; detail?: string; needs_owner_decision?: boolean },
    ) =>
      request(`/delivery/tasks/${taskId}/blockers/`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    resolveBlocker: (taskId: number, blockerId: number, note?: string) =>
      request(`/delivery/tasks/${taskId}/blockers/${blockerId}/resolve/`, {
        method: "POST",
        body: JSON.stringify({ note: note || "" }),
      }),
    createHandoff: (
      taskId: number,
      data: {
        from_role?: string;
        to_role: string;
        done_summary: string;
        left_summary?: string;
        branch_or_pr_url?: string;
        checks_url?: string;
        open_questions?: string;
        needs_owner_decision?: boolean;
      },
    ) =>
      request<{ handoff: unknown; task: DeliveryTask }>(
        `/delivery/tasks/${taskId}/handoffs/`,
        {
          method: "POST",
          body: JSON.stringify(data),
        },
      ),
    addDependency: (taskId: number, dependsOn: number) =>
      request(`/delivery/tasks/${taskId}/dependencies/`, {
        method: "POST",
        body: JSON.stringify({ depends_on: dependsOn }),
      }),
    getHistory: (taskId: number) =>
      request<{
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
      }>(`/delivery/tasks/${taskId}/history/`),
    prSnippet: (taskId: number) =>
      request<{ markdown: string; task_id: number }>(
        `/delivery/tasks/${taskId}/pr-snippet/`,
      ),
    queue: (params?: { role?: string; status?: string }) =>
      request<DeliveryTask[]>(`/delivery/queue/${qs(params)}`),
  };
}

export type DeliveryApi = ReturnType<typeof createDeliveryApi>;
