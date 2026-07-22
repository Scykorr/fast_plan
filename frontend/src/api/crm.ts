import { request } from "./client";

export type CrmOrganization = {
  id: number;
  name: string;
  website: string;
  industry: string;
  notes: string;
  people_count?: number;
  projects_count?: number;
  created_at: string;
  updated_at: string;
};

export type CrmPersonOrg = {
  id: number;
  name: string;
  title: string;
  is_primary: boolean;
};

export type CrmPerson = {
  id: number;
  full_name: string;
  email: string;
  phone: string;
  job_title: string;
  notes: string;
  birth_date: string | null;
  remind_before_days: number;
  organizations: CrmPersonOrg[];
  projects_count?: number;
  legacy_contact_id: number | null;
  user_id: number | null;
  created_at: string;
  updated_at: string;
};

export type CrmActivity = {
  id: number;
  kind: "call" | "meeting" | "email" | "note" | "other";
  subject: string;
  body: string;
  occurred_at: string;
  person: number | null;
  person_name: string | null;
  organization: number | null;
  organization_name: string | null;
  project: number | null;
  project_name: string | null;
  created_by: number | null;
  created_by_email: string | null;
  created_at: string;
};

export function createCrmApi() {
  return {
    listOrganizations: (q = "") => {
      const qs = q ? `?q=${encodeURIComponent(q)}` : "";
      return request<CrmOrganization[]>(`/crm/organizations/${qs}`, {});
    },
    createOrganization: (body: Partial<CrmOrganization>) =>
      request<CrmOrganization>("/crm/organizations/", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    patchOrganization: (id: number, body: Partial<CrmOrganization>) =>
      request<CrmOrganization>(`/crm/organizations/${id}/`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    deleteOrganization: (id: number) =>
      request<void>(`/crm/organizations/${id}/`, { method: "DELETE" }),

    listPeople: (q = "") => {
      const qs = q ? `?q=${encodeURIComponent(q)}` : "";
      return request<CrmPerson[]>(`/crm/people/${qs}`, {});
    },
    createPerson: (body: Record<string, unknown>) =>
      request<CrmPerson>("/crm/people/", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    patchPerson: (id: number, body: Record<string, unknown>) =>
      request<CrmPerson>(`/crm/people/${id}/`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    deletePerson: (id: number) =>
      request<void>(`/crm/people/${id}/`, { method: "DELETE" }),

    listActivities: (params: {
      person_id?: number;
      organization_id?: number;
      project_id?: number;
    } = {}) => {
      const qs = new URLSearchParams();
      if (params.person_id) qs.set("person_id", String(params.person_id));
      if (params.organization_id) {
        qs.set("organization_id", String(params.organization_id));
      }
      if (params.project_id) qs.set("project_id", String(params.project_id));
      const suffix = qs.toString() ? `?${qs}` : "";
      return request<CrmActivity[]>(`/crm/activities/${suffix}`, {});
    },
    createActivity: (body: Record<string, unknown>) =>
      request<CrmActivity>("/crm/activities/", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    deleteActivity: (id: number) =>
      request<void>(`/crm/activities/${id}/`, { method: "DELETE" }),

    importLegacy: () =>
      request<{
        imported_contacts: number;
        imported_stakeholders: number;
        synced_at: string;
      }>("/crm/import-legacy/", { method: "POST", body: "{}" }),
  };
}

export type CrmApi = ReturnType<typeof createCrmApi>;
