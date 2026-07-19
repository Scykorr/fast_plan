export type DeepLinkParams = {
  workspace?: number | null;
  tab?: string | null;
  node?: number | null;
  card?: number | null;
  risk?: number | null;
  assignee?: number | null;
  status?: number | null;
  project?: number | null;
};

const INT_KEYS = [
  "workspace",
  "node",
  "card",
  "risk",
  "assignee",
  "status",
  "project",
] as const;

function parseOptionalInt(value: string | null): number | null {
  if (value == null || value === "") {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function parseDeepLinkParams(
  searchParams: URLSearchParams,
): DeepLinkParams {
  return {
    workspace: parseOptionalInt(searchParams.get("workspace")),
    tab: searchParams.get("tab") || null,
    node: parseOptionalInt(searchParams.get("node")),
    card: parseOptionalInt(searchParams.get("card")),
    risk: parseOptionalInt(searchParams.get("risk")),
    assignee: parseOptionalInt(searchParams.get("assignee")),
    status: parseOptionalInt(searchParams.get("status")),
    project: parseOptionalInt(searchParams.get("project")),
  };
}

export function buildDeepLinkSearch(
  params: DeepLinkParams,
): URLSearchParams {
  const next = new URLSearchParams();
  if (params.workspace != null) {
    next.set("workspace", String(params.workspace));
  }
  if (params.tab) {
    next.set("tab", params.tab);
  }
  for (const key of INT_KEYS) {
    if (key === "workspace") {
      continue;
    }
    const value = params[key];
    if (value != null) {
      next.set(key, String(value));
    }
  }
  return next;
}

/** Merge updates into current params. Pass `null` to remove a key. */
export function mergeDeepLinkSearch(
  current: URLSearchParams,
  updates: DeepLinkParams,
): URLSearchParams {
  const next = new URLSearchParams(current);
  if ("workspace" in updates) {
    if (updates.workspace == null) {
      next.delete("workspace");
    } else {
      next.set("workspace", String(updates.workspace));
    }
  }
  if ("tab" in updates) {
    if (!updates.tab) {
      next.delete("tab");
    } else {
      next.set("tab", updates.tab);
    }
  }
  for (const key of INT_KEYS) {
    if (key === "workspace" || !(key in updates)) {
      continue;
    }
    const value = updates[key];
    if (value == null) {
      next.delete(key);
    } else {
      next.set(key, String(value));
    }
  }
  return next;
}
