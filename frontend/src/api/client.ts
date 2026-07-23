const API_BASE = "/api";
const WORKSPACE_STORAGE_KEY = "fast_plan_workspace";

export type User = {
  id: number;
  email: string;
  username: string;
  first_name: string;
  last_name: string;
  avatar_url: string | null;
  is_email_verified: boolean;
  is_totp_enabled: boolean;
  date_joined: string;
  active_workspace_id: number | null;
  active_workspace_name: string | null;
};

export type AuthSessionRow = {
  id: number;
  user_agent: string;
  ip_address: string;
  created_at: string;
  last_seen_at: string;
  is_current: boolean;
};

export type LoginResult =
  | { requires_2fa: true; pre_auth_token: string; detail: string }
  | { requires_2fa?: false; detail: string; user: User };

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

function readCookie(name: string): string | null {
  const match = document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`));
  if (!match) {
    return null;
  }
  return decodeURIComponent(match.slice(name.length + 1));
}

export function getCsrfToken(): string | null {
  return readCookie("csrftoken");
}

let refreshPromise: Promise<boolean> | null = null;

async function ensureCsrfCookie(): Promise<string | null> {
  const existing = getCsrfToken();
  if (existing) {
    return existing;
  }
  try {
    await fetch(`${API_BASE}/auth/csrf/`, {
      method: "GET",
      credentials: "include",
    });
  } catch {
    return getCsrfToken();
  }
  return getCsrfToken();
}

async function refreshSession(): Promise<boolean> {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const csrf = await ensureCsrfCookie();
        const headers: Record<string, string> = {
          "Content-Type": "application/json",
        };
        if (csrf) {
          headers["X-CSRFToken"] = csrf;
        }
        const response = await fetch(`${API_BASE}/auth/refresh/`, {
          method: "POST",
          credentials: "include",
          headers,
          body: "{}",
        });
        return response.ok;
      } catch {
        return false;
      }
    })().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  { retry = true }: { retry?: boolean } = {},
): Promise<T> {
  const method = (options.method ?? "GET").toUpperCase();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (activeWorkspaceId != null && !headers["X-Workspace-Id"]) {
    headers["X-Workspace-Id"] = String(activeWorkspaceId);
  }

  if (!["GET", "HEAD", "OPTIONS", "TRACE"].includes(method)) {
    const csrf = await ensureCsrfCookie();
    if (csrf) {
      headers["X-CSRFToken"] = csrf;
    }
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    method,
    headers,
    credentials: "include",
  });

  if (response.status === 401 && retry && path !== "/auth/refresh/") {
    const refreshed = await refreshSession();
    if (refreshed) {
      return request<T>(path, options, { retry: false });
    }
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new ApiError(response.status, data);
  }

  return data as T;
}

async function requestBlob(
  path: string,
  options: RequestInit = {},
  { retry = true }: { retry?: boolean } = {},
): Promise<Blob> {
  const method = (options.method ?? "GET").toUpperCase();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  if (activeWorkspaceId != null && !headers["X-Workspace-Id"]) {
    headers["X-Workspace-Id"] = String(activeWorkspaceId);
  }

  if (!["GET", "HEAD", "OPTIONS", "TRACE"].includes(method)) {
    const csrf = await ensureCsrfCookie();
    if (csrf) {
      headers["X-CSRFToken"] = csrf;
    }
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    method,
    headers,
    credentials: "include",
  });

  if (response.status === 401 && retry && path !== "/auth/refresh/") {
    const refreshed = await refreshSession();
    if (refreshed) {
      return requestBlob(path, options, { retry: false });
    }
  }

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new ApiError(response.status, data);
  }

  return response.blob();
}

async function requestForm<T>(
  path: string,
  formData: FormData,
  method = "POST",
  { retry = true }: { retry?: boolean } = {},
): Promise<T> {
  const headers: Record<string, string> = {};

  if (activeWorkspaceId != null) {
    headers["X-Workspace-Id"] = String(activeWorkspaceId);
  }

  const csrf = await ensureCsrfCookie();
  if (csrf) {
    headers["X-CSRFToken"] = csrf;
  }

  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: formData,
    credentials: "include",
  });

  if (response.status === 401 && retry) {
    const refreshed = await refreshSession();
    if (refreshed) {
      return requestForm<T>(path, formData, method, { retry: false });
    }
  }

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new ApiError(response.status, data);
  }

  return data as T;
}

export const api = {
  ensureCsrf: () => ensureCsrfCookie(),

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

  login: async (body: { email: string; password: string }) => {
    await ensureCsrfCookie();
    return request<LoginResult>("/auth/login/", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  verify2fa: async (body: { pre_auth_token: string; code: string }) => {
    await ensureCsrfCookie();
    return request<{ detail: string; user: User }>("/auth/2fa/verify/", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  setup2fa: () =>
    request<{ secret: string; otpauth_url: string }>("/auth/2fa/setup/", {
      method: "POST",
      body: "{}",
    }),

  enable2fa: (code: string) =>
    request<{ detail: string; backup_codes: string[]; user: User }>(
      "/auth/2fa/enable/",
      {
        method: "POST",
        body: JSON.stringify({ code }),
      },
    ),

  disable2fa: (body: { password: string; code: string }) =>
    request<{ detail: string; user: User }>("/auth/2fa/disable/", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  listAuthSessions: () => request<AuthSessionRow[]>("/auth/sessions/"),

  revokeAuthSession: (sessionId: number) =>
    request<{ detail: string }>(`/auth/sessions/${sessionId}/revoke/`, {
      method: "POST",
      body: "{}",
    }),

  revokeOtherSessions: () =>
    request<{ revoked: number }>("/auth/sessions/revoke-others/", {
      method: "POST",
      body: "{}",
    }),

  me: () => request<User>("/auth/me/"),

  updateProfile: (formData: FormData) =>
    requestForm<User>("/auth/me/", formData, "PATCH"),

  verifyEmail: (body: { uid: string; token: string }) =>
    request<{ detail: string }>("/auth/email/verify/", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  resendVerification: (email: string) =>
    request<{ detail: string }>("/auth/email/resend/", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  oauthProviders: () =>
    request<{ google: boolean; microsoft: boolean }>("/auth/oauth/providers/"),
  oauthStartUrl: (provider: "microsoft", next?: string | null) => {
    const q = next ? `?next=${encodeURIComponent(next)}` : "";
    return `${API_BASE}/auth/oauth/${provider}/${q}`;
  },

  refresh: () => refreshSession(),

  logout: () =>
    request<{ detail: string }>("/auth/logout/", {
      method: "POST",
      body: "{}",
    }),

  forgotPassword: (email: string) =>
    request<{ detail: string }>("/auth/password/forgot/", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),

  resetPassword: (body: { uid: string; token: string; new_password: string }) =>
    request<{ detail: string }>("/auth/password/reset/", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  changePassword: (body: { current_password: string; new_password: string }) =>
    request<{ detail: string }>("/auth/password/change/", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};

export { ApiError, request, requestBlob, requestForm, WORKSPACE_STORAGE_KEY };
