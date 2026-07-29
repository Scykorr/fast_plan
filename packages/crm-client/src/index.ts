/**
 * Typed Fast Plan CRM client.
 *
 * Prefer regenerating types from OpenAPI when the schema changes:
 *   1. Backend: GET /api/schema/ (drf-spectacular)
 *   2. packages/crm-client: npm run generate -- --schema http://127.0.0.1:8000/api/schema/
 *
 * Until codegen is wired in CI, hand-maintained types cover the CRM surface
 * used by integrators (orgs, people, deals, leads, custom fields, graphql lite).
 */

export type CrmCustomFieldTarget = "organization" | "person" | "deal" | "lead";

export type CrmCustomFieldDefinition = {
  id: number;
  target: CrmCustomFieldTarget | string;
  key: string;
  label: string;
  field_type: "text" | "number" | "bool" | "date" | "select" | "multi_select" | string;
  options: string[];
  required: boolean;
  position: number;
  is_active: boolean;
};

export type CrmOrganization = {
  id: number;
  name: string;
  website?: string;
  industry?: string;
  notes?: string;
};

export type CrmPerson = {
  id: number;
  full_name: string;
  email?: string;
  phone?: string;
};

export type CrmDeal = {
  id: number;
  title: string;
  amount?: string | number;
  stage?: number;
  stage_name?: string;
};

export type CrmLead = {
  id: number;
  full_name: string;
  status?: string;
  score?: number;
  source?: string;
};

export type CrmClientOptions = {
  baseUrl: string;
  /** API token (Authorization: Token …) or leave empty for cookie session */
  token?: string;
  workspaceId?: number | string;
  fetch?: typeof fetch;
};

function joinUrl(base: string, path: string) {
  return `${base.replace(/\/$/, "")}${path.startsWith("/") ? path : `/${path}`}`;
}

export class FastPlanCrmClient {
  private baseUrl: string;
  private token?: string;
  private workspaceId?: number | string;
  private fetchImpl: typeof fetch;

  constructor(opts: CrmClientOptions) {
    this.baseUrl = opts.baseUrl;
    this.token = opts.token;
    this.workspaceId = opts.workspaceId;
    this.fetchImpl = opts.fetch ?? fetch;
  }

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      Accept: "application/json",
      ...(init.headers as Record<string, string> | undefined),
    };
    if (init.body && !headers["Content-Type"]) {
      headers["Content-Type"] = "application/json";
    }
    if (this.token) {
      headers.Authorization = `Token ${this.token}`;
    }
    if (this.workspaceId != null) {
      headers["X-Workspace-Id"] = String(this.workspaceId);
    }
    const res = await this.fetchImpl(joinUrl(this.baseUrl, path), {
      ...init,
      headers,
    });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(`CRM API ${res.status}: ${text || res.statusText}`);
    }
    if (res.status === 204) {
      return undefined as T;
    }
    return (await res.json()) as T;
  }

  listOrganizations() {
    return this.request<CrmOrganization[]>("/api/crm/organizations/");
  }

  listPeople() {
    return this.request<CrmPerson[]>("/api/crm/people/");
  }

  listDeals() {
    return this.request<CrmDeal[]>("/api/crm/deals/");
  }

  listLeads() {
    return this.request<CrmLead[]>("/api/crm/leads/");
  }

  listCustomFields(target?: CrmCustomFieldTarget) {
    const q = target ? `?target=${encodeURIComponent(target)}` : "";
    return this.request<CrmCustomFieldDefinition[]>(`/api/crm/custom-fields/${q}`);
  }

  getEntityCustomFields(target: CrmCustomFieldTarget, entityId: number) {
    return this.request<{
      target: string;
      entity_id: number;
      values: Record<string, unknown>;
      definitions: CrmCustomFieldDefinition[];
    }>(`/api/crm/${target}/${entityId}/custom-fields/`);
  }

  putEntityCustomFields(
    target: CrmCustomFieldTarget,
    entityId: number,
    values: Record<string, unknown>,
  ) {
    return this.request<{
      target: string;
      entity_id: number;
      values: Record<string, unknown>;
    }>(`/api/crm/${target}/${entityId}/custom-fields/`, {
      method: "PUT",
      body: JSON.stringify({ values }),
    });
  }

  graphql(query: string) {
    return this.request<{ data: Record<string, unknown> }>("/api/crm/graphql/", {
      method: "POST",
      body: JSON.stringify({ query }),
    });
  }
}

export function createCrmClient(opts: CrmClientOptions) {
  return new FastPlanCrmClient(opts);
}
