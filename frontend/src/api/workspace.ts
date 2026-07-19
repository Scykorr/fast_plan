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

export type WorkspaceDashboard = {
  workspace_id: number;
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

    acceptInvitation: (tokenValue: string) =>
      request<{ workspace_id: number; name: string; role: string | null }>(
        `/workspace/invitations/${tokenValue}/accept/`,
        { method: "POST" }
      ),
  };
}
