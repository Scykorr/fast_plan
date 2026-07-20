import { request } from "./client";

export type WorkspaceSummary = {
  id: number;
  name: string;
  role: "owner" | "editor" | "viewer" | string;
  is_active: boolean;
};

export type WorkspaceMember = {
  id: number;
  user_id: number;
  email: string;
  username: string;
  role: string;
  joined_at: string;
};

export type WorkspaceInvitation = {
  id: number;
  email: string;
  role: string;
  token: string;
  expires_at: string;
  accepted_at: string | null;
  created_at: string;
};

export type WorkspaceAPIToken = {
  id: number;
  name: string;
  prefix: string;
  scopes: string[];
  created_at: string;
  last_used_at: string | null;
  expires_at: string | null;
  revoked_at: string | null;
  token?: string;
};

export type WebhookEndpoint = {
  id: number;
  name: string;
  url: string;
  events: string[];
  is_active: boolean;
  created_at: string;
  secret?: string;
};

export type WorkspaceDashboard = {
  workspace_id: number;
  currency?: string;
  generated_at: string;
  summary: {
    project_count: number;
    overdue_count: number;
    open_risk_count: number;
    unread_notification_count: number;
  };
  overdue_tasks: Array<{
    activity_id: number;
    wbs_id: number;
    wbs_code: string;
    title: string;
    project_id: number;
    project_name: string;
    end_date: string;
    progress: number;
    assignee_id: number | null;
    assignee_name: string | null;
    days_overdue: number;
  }>;
  top_risks: Array<{
    id: number;
    title: string;
    score: number;
    probability: number;
    impact: number;
    status: string;
    project_id: number;
    project_name: string;
  }>;
  project_health: Array<{
    project_id: number;
    name: string;
    status: string;
    progress: number;
    budget: number;
    spi: number | null;
    cpi: number | null;
    overdue_count: number;
  }>;
  unread_notifications: Array<{
    id: number;
    notification_type: string;
    title: string;
    message: string;
    link: string;
    created_at: string;
  }>;
};

export type ExchangeRateRow = {
  id: number | null;
  currency: string;
  rate_to_base: string;
  as_of: string | null;
  created_at: string | null;
};

export type WorkspaceSettings = {
  workspace_id: number;
  currency: string;
  exchange_rates: ExchangeRateRow[];
};

export type SearchResult = {
  type: "project" | "wbs" | "card" | "risk" | "contact" | string;
  id: number;
  title: string;
  subtitle: string;
  project_id: number | null;
  project_name: string | null;
  link: string;
  extra: Record<string, unknown>;
};

export type MyTask = {
  wbs_id: number;
  wbs_code: string;
  title: string;
  node_type: string;
  project_id: number;
  project_name: string;
  assignee_id: number | null;
  assignee_name: string | null;
  workflow_status_id: number | null;
  workflow_status_name: string | null;
  progress: number;
  start_date: string | null;
  end_date: string | null;
  days_overdue: number;
  card_id: number | null;
  board_id: number | null;
  link: string;
};

export type CapacityMember = {
  user_id: number;
  name: string;
  email: string;
  role: string;
  capacity_hours: number;
  allocated_hours: number;
  utilization: number | null;
  assignments: Array<{
    wbs_id: number;
    title: string;
    project_id: number;
    project_name: string;
    hours: number;
    overlap_days: number;
  }>;
};

export function createWorkspaceApi() {
  return {
    listWorkspaces: () =>
      request<WorkspaceSummary[]>("/workspaces/", {}),

    activateWorkspace: (workspaceId: number) =>
      request<WorkspaceSummary>(
        `/workspaces/${workspaceId}/activate/`,
        { method: "POST" }
      ),

    getDashboard: () =>
      request<WorkspaceDashboard>("/workspace/dashboard/", {}),

    getSettings: () =>
      request<WorkspaceSettings>("/workspace/settings/", {}),

    patchSettings: (body: { currency?: string }) =>
      request<WorkspaceSettings>("/workspace/settings/", {
        method: "PATCH",
        body: JSON.stringify(body),
      }),

    getExchangeRates: () =>
      request<ExchangeRateRow[]>("/workspace/exchange-rates/", {}),

    createExchangeRate: (body: {
      currency: string;
      rate_to_base: string;
      as_of?: string;
    }) =>
      request<ExchangeRateRow>("/workspace/exchange-rates/", {
        method: "POST",
        body: JSON.stringify(body),
      }),

    deleteExchangeRate: (rateId: number) =>
      request<void>(`/workspace/exchange-rates/${rateId}/`, {
        method: "DELETE",
      }),

    getMembers: () =>
      request<WorkspaceMember[]>("/workspace/members/", {}),

    inviteMember: (email: string, role = "editor") =>
      request<WorkspaceInvitation>(
        "/workspace/invitations/",
        {
          method: "POST",
          body: JSON.stringify({ email, role }),
        }
      ),

    getInvitations: () =>
      request<WorkspaceInvitation[]>("/workspace/invitations/", {}),

    revokeInvitation: (invitationId: number) =>
      request<void>(`/workspace/invitations/${invitationId}/`, {
        method: "DELETE",
      }),

    resendInvitation: (invitationId: number) =>
      request<WorkspaceInvitation>(
        `/workspace/invitations/${invitationId}/resend/`,
        { method: "POST" },
      ),

    acceptInvitation: (tokenValue: string) =>
      request<{ workspace_id: number; name: string; role: string | null }>(
        `/workspace/invitations/${tokenValue}/accept/`,
        { method: "POST" }
      ),

    search: (q: string, limit = 20) =>
      request<{ workspace_id: number; query: string; results: SearchResult[] }>(
        `/workspace/search/?q=${encodeURIComponent(q)}&limit=${limit}`,
        {},
      ),

    getMyTasks: (params?: {
      assignee?: number;
      include_done?: boolean;
      overdue_only?: boolean;
    }) => {
      const query = new URLSearchParams();
      if (params?.assignee != null) {
        query.set("assignee", String(params.assignee));
      }
      if (params?.include_done) {
        query.set("include_done", "true");
      }
      if (params?.overdue_only) {
        query.set("overdue_only", "true");
      }
      const suffix = query.toString() ? `?${query.toString()}` : "";
      return request<{
        workspace_id: number;
        assignee_id: number;
        assignee_name: string;
        summary: { total: number; overdue: number; due_soon: number };
        tasks: MyTask[];
      }>(`/workspace/my-tasks/${suffix}`, {});
    },

    getCapacity: (weekStart?: string) => {
      const suffix = weekStart
        ? `?week_start=${encodeURIComponent(weekStart)}`
        : "";
      return request<{
        workspace_id: number;
        week_start: string;
        week_end: string;
        members: CapacityMember[];
      }>(`/workspace/capacity/${suffix}`, {});
    },

    setCapacity: (userId: number, hoursPerWeek: number) =>
      request<{ user_id: number; hours_per_week: number }>(
        "/workspace/capacity/",
        {
          method: "PATCH",
          body: JSON.stringify({
            user_id: userId,
            hours_per_week: hoursPerWeek,
          }),
        },
      ),

    getApiTokens: () =>
      request<WorkspaceAPIToken[]>("/workspace/api-tokens/", {}),

    createApiToken: (name: string, scopes: string[]) =>
      request<WorkspaceAPIToken>("/workspace/api-tokens/", {
        method: "POST",
        body: JSON.stringify({ name, scopes }),
      }),

    revokeApiToken: (tokenId: number) =>
      request<void>(`/workspace/api-tokens/${tokenId}/`, { method: "DELETE" }),

    getWebhooks: () =>
      request<WebhookEndpoint[]>("/workspace/webhooks/", {}),

    createWebhook: (body: {
      name: string;
      url: string;
      events: string[];
    }) =>
      request<WebhookEndpoint>("/workspace/webhooks/", {
        method: "POST",
        body: JSON.stringify(body),
      }),

    deleteWebhook: (endpointId: number) =>
      request<void>(`/workspace/webhooks/${endpointId}/`, { method: "DELETE" }),

    testWebhook: (endpointId: number) =>
      request<{
        delivery_id: number;
        status: string;
        status_code: number | null;
        error: string;
      }>(`/workspace/webhooks/${endpointId}/test/`, { method: "POST" }),
  };
}
