import { request, requestForm } from "./client";

export type CrmTag = {
  id: number;
  name: string;
  color: string;
  created_at: string;
};

export type CrmOrganization = {
  id: number;
  name: string;
  website: string;
  industry: string;
  notes: string;
  owner_id: number | null;
  owner_email: string | null;
  tags: CrmTag[];
  people_count?: number;
  projects_count?: number;
  last_activity_at: string | null;
  days_since_touch: number | null;
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
  telegram: string;
  whatsapp: string;
  social_urls: string[];
  job_title: string;
  notes: string;
  birth_date: string | null;
  remind_before_days: number;
  owner_id: number | null;
  owner_email: string | null;
  tags: CrmTag[];
  organizations: CrmPersonOrg[];
  projects_count?: number;
  last_activity_at: string | null;
  days_since_touch: number | null;
  legacy_contact_id: number | null;
  user_id: number | null;
  created_at: string;
  updated_at: string;
};

export type CrmActivityKind =
  | "call"
  | "meeting"
  | "email"
  | "note"
  | "invoice"
  | "order"
  | "other";

export type CrmActivity = {
  id: number;
  kind: CrmActivityKind;
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

export type CrmSegment = {
  id: number;
  name: string;
  kind: "manual" | "rule";
  rule: Record<string, unknown>;
  people_count: number;
  organizations_count: number;
  created_at: string;
  updated_at: string;
};

export type CrmComment = {
  id: number;
  body: string;
  person: number | null;
  organization: number | null;
  author: number | null;
  author_email: string | null;
  created_at: string;
  updated_at: string;
};

export type CrmAttachment = {
  id: number;
  name: string;
  size: number;
  content_type: string;
  url: string | null;
  person: number | null;
  organization: number | null;
  uploaded_by: number | null;
  uploaded_by_email: string | null;
  created_at: string;
};

export type CrmListParams = {
  q?: string;
  tag_id?: number;
  segment_id?: number;
  stale_days?: number;
};

function listQuery(params: CrmListParams = {}) {
  const qs = new URLSearchParams();
  if (params.q) qs.set("q", params.q);
  if (params.tag_id) qs.set("tag_id", String(params.tag_id));
  if (params.segment_id) qs.set("segment_id", String(params.segment_id));
  if (params.stale_days) qs.set("stale_days", String(params.stale_days));
  const suffix = qs.toString() ? `?${qs}` : "";
  return suffix;
}

export function createCrmApi() {
  return {
    listOrganizations: (params: CrmListParams | string = {}) => {
      const query =
        typeof params === "string" ? listQuery({ q: params }) : listQuery(params);
      return request<CrmOrganization[]>(`/crm/organizations/${query}`, {});
    },
    createOrganization: (body: Record<string, unknown>) =>
      request<CrmOrganization>("/crm/organizations/", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    patchOrganization: (id: number, body: Record<string, unknown>) =>
      request<CrmOrganization>(`/crm/organizations/${id}/`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    deleteOrganization: (id: number) =>
      request<void>(`/crm/organizations/${id}/`, { method: "DELETE" }),
    attachOrganizationTag: (orgId: number, body: { tag_id?: number; name?: string }) =>
      request<CrmTag>(`/crm/organizations/${orgId}/tags/`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    detachOrganizationTag: (orgId: number, tagId: number) =>
      request<void>(`/crm/organizations/${orgId}/tags/${tagId}/`, {
        method: "DELETE",
      }),

    listPeople: (params: CrmListParams | string = {}) => {
      const query =
        typeof params === "string" ? listQuery({ q: params }) : listQuery(params);
      return request<CrmPerson[]>(`/crm/people/${query}`, {});
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
    attachPersonTag: (personId: number, body: { tag_id?: number; name?: string }) =>
      request<CrmTag>(`/crm/people/${personId}/tags/`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    detachPersonTag: (personId: number, tagId: number) =>
      request<void>(`/crm/people/${personId}/tags/${tagId}/`, {
        method: "DELETE",
      }),

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

    listTags: () => request<CrmTag[]>("/crm/tags/", {}),
    createTag: (body: { name: string; color?: string }) =>
      request<CrmTag>("/crm/tags/", {
        method: "POST",
        body: JSON.stringify(body),
      }),

    listSegments: () => request<CrmSegment[]>("/crm/segments/", {}),
    createSegment: (body: Record<string, unknown>) =>
      request<CrmSegment>("/crm/segments/", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    deleteSegment: (id: number) =>
      request<void>(`/crm/segments/${id}/`, { method: "DELETE" }),

    listComments: (params: { person_id?: number; organization_id?: number } = {}) => {
      const qs = new URLSearchParams();
      if (params.person_id) qs.set("person_id", String(params.person_id));
      if (params.organization_id) {
        qs.set("organization_id", String(params.organization_id));
      }
      const suffix = qs.toString() ? `?${qs}` : "";
      return request<CrmComment[]>(`/crm/comments/${suffix}`, {});
    },
    createComment: (body: Record<string, unknown>) =>
      request<CrmComment>("/crm/comments/", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    deleteComment: (id: number) =>
      request<void>(`/crm/comments/${id}/`, { method: "DELETE" }),

    listAttachments: (params: {
      person_id?: number;
      organization_id?: number;
    } = {}) => {
      const qs = new URLSearchParams();
      if (params.person_id) qs.set("person_id", String(params.person_id));
      if (params.organization_id) {
        qs.set("organization_id", String(params.organization_id));
      }
      const suffix = qs.toString() ? `?${qs}` : "";
      return request<CrmAttachment[]>(`/crm/attachments/${suffix}`, {});
    },
    uploadAttachment: (params: {
      file: File;
      person_id?: number;
      organization_id?: number;
    }) => {
      const form = new FormData();
      form.append("file", params.file);
      if (params.person_id) form.append("person_id", String(params.person_id));
      if (params.organization_id) {
        form.append("organization_id", String(params.organization_id));
      }
      return requestForm<CrmAttachment>("/crm/attachments/", form);
    },
    deleteAttachment: (id: number) =>
      request<void>(`/crm/attachments/${id}/`, { method: "DELETE" }),

    importLegacy: () =>
      request<{
        imported_contacts: number;
        imported_stakeholders: number;
        synced_at: string;
      }>("/crm/import-legacy/", { method: "POST", body: "{}" }),
  };
}

export type CrmApi = ReturnType<typeof createCrmApi>;
