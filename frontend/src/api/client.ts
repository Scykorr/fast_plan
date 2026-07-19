const API_BASE = "/api";
const WORKSPACE_STORAGE_KEY = "fast_plan_workspace";

export type User = {
  id: number;
  email: string;
  username: string;
  first_name: string;
  last_name: string;
  date_joined: string;
  active_workspace_id: number | null;
  active_workspace_name: string | null;
};

export type AuthTokens = {
  access: string;
  refresh: string;
};

class ApiError extends Error {
  status: number;
  data: Record<string, unknown>;

  constructor(status: number, data: Record<string, unknown>) {
    super("API request failed");
    this.status = status;
    this.data = data;
  }
}

let activeWorkspaceId: number | null = (() => {
  const stored = localStorage.getItem(WORKSPACE_STORAGE_KEY);
  if (!stored) {
    return null;
  }
  const parsed = Number(stored);
  return Number.isFinite(parsed) ? parsed : null;
})();

export function getActiveWorkspaceId(): number | null {
  return activeWorkspaceId;
}

export function setActiveWorkspaceId(workspaceId: number | null): void {
  activeWorkspaceId = workspaceId;
  if (workspaceId == null) {
    localStorage.removeItem(WORKSPACE_STORAGE_KEY);
  } else {
    localStorage.setItem(WORKSPACE_STORAGE_KEY, String(workspaceId));
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string | null,
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  if (activeWorkspaceId != null && !headers["X-Workspace-Id"]) {
    headers["X-Workspace-Id"] = String(activeWorkspaceId);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new ApiError(response.status, data);
  }

  return data as T;
}

export const api = {
  register: (body: {
    email: string;
    username: string;
    password: string;
    first_name?: string;
    last_name?: string;
  }) =>
    request<User>("/auth/register/", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  login: (body: { email: string; password: string }) =>
    request<AuthTokens>("/auth/login/", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  me: (token: string) => request<User>("/auth/me/", {}, token),

  refresh: (refresh: string) =>
    request<{ access: string }>("/auth/refresh/", {
      method: "POST",
      body: JSON.stringify({ refresh }),
    }),
};

export { ApiError, request, WORKSPACE_STORAGE_KEY };
