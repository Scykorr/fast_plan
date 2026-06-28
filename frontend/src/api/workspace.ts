import { request } from "./client";

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

export function createWorkspaceApi(token: string) {
  return {
    getMembers: () =>
      request<WorkspaceMember[]>("/workspace/members/", {}, token),

    inviteMember: (email: string, role = "editor") =>
      request<WorkspaceInvitation>("/workspace/invitations/", {
        method: "POST",
        body: JSON.stringify({ email, role }),
      }, token),

    getInvitations: () =>
      request<WorkspaceInvitation[]>("/workspace/invitations/", {}, token),

    acceptInvitation: (tokenValue: string) =>
      request<{ workspace_id: number; name: string }>(
        `/workspace/invitations/${tokenValue}/accept/`,
        { method: "POST" },
        token,
      ),
  };
}
