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

export type CrmPipelineStage = {
  id: number;
  name: string;
  position: number;
  default_probability: number;
  is_won: boolean;
  is_lost: boolean;
};

export type CrmPipeline = {
  id: number;
  name: string;
  is_default: boolean;
  stages: CrmPipelineStage[];
  created_at: string;
};

export type CrmDeal = {
  id: number;
  pipeline: number;
  stage: number;
  stage_name: string;
  title: string;
  amount: string | number;
  probability: number;
  weighted_amount: number;
  close_date: string | null;
  organization: number | null;
  organization_name: string | null;
  person: number | null;
  person_name: string | null;
  project: number | null;
  project_name: string | null;
  owner: number | null;
  owner_email: string | null;
  position: number;
  notes: string;
  is_open: boolean;
  open_tasks_count?: number;
  created_at: string;
  updated_at: string;
};

export type CrmDealForecast = {
  open_count: number;
  open_amount: number;
  forecast_amount: number;
  won_count: number;
  won_amount: number;
  lost_count: number;
  lost_amount: number;
};

export type CrmDealTask = {
  id: number;
  deal: number;
  title: string;
  due_date: string | null;
  is_done: boolean;
  assignee: number | null;
  assignee_email: string | null;
  remind_before_days: number;
  notes: string;
  created_at: string;
  updated_at: string;
};

export type CrmLeadStatus =
  | "new"
  | "contacted"
  | "qualified"
  | "disqualified"
  | "converted";

export type CrmLead = {
  id: number;
  full_name: string;
  email: string;
  phone: string;
  company_name: string;
  source: string;
  status: CrmLeadStatus;
  score: number;
  assigned_to: number | null;
  assigned_to_email: string | null;
  organization: number | null;
  organization_name: string | null;
  person: number | null;
  deal: number | null;
  deal_title: string | null;
  notes: string;
  duplicate_ids?: number[];
  created_at: string;
  updated_at: string;
};

export type CrmAutomationTrigger =
  | "lead.created"
  | "lead.converted"
  | "deal.created"
  | "deal.stage_changed"
  | "schedule.daily";

export type CrmAutomationCondition = {
  field: string;
  op: string;
  value: unknown;
};

export type CrmAutomationAction = {
  type: string;
  [key: string]: unknown;
};

export type CrmAutomationRule = {
  id: number;
  name: string;
  is_active: boolean;
  trigger: CrmAutomationTrigger | string;
  conditions: CrmAutomationCondition[];
  actions: CrmAutomationAction[];
  template_key: string;
  created_at: string;
  updated_at: string;
};

export type CrmAutomationTemplate = {
  key: string;
  name: string;
  trigger: string;
  conditions: CrmAutomationCondition[];
  actions: CrmAutomationAction[];
};

export type CrmAiInsights = {
  summary: string;
  source: string;
  stale_days: number;
  forecast_amount: number;
  stale_people: Array<{
    id: number;
    full_name: string;
    email: string;
    days_since_touch: number | null;
  }>;
  stale_organizations: Array<{
    id: number;
    name: string;
    days_since_touch: number | null;
  }>;
  at_risk_deals: Array<{
    id: number;
    title: string;
    amount: number;
    probability: number;
    close_date: string | null;
    days_since_touch: number;
    reasons: string[];
    organization_name: string | null;
  }>;
};

export type CrmAiDraftEmail = {
  subject: string;
  body: string;
  source: string;
};

export type CrmAiDraftKp = {
  title: string;
  markdown: string;
  source: string;
};

export type CrmAiActivitySummary = {
  summary: string;
  highlights: string[];
  source: string;
  count: number;
};

export type CrmAiSuggestTasks = {
  tasks: Array<{ title: string; due_in_days: number; notes: string }>;
  created: Array<{ id: number; title: string; due_date: string }>;
  source: string;
};

export type CrmAutomationRun = {
  id: number;
  rule: number;
  rule_name: string;
  trigger: string;
  context: Record<string, unknown>;
  result: Record<string, unknown>;
  success: boolean;
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

    getPipeline: () => request<CrmPipeline>("/crm/pipeline/", {}),
    listDeals: (params: {
      stage_id?: number;
      organization_id?: number;
      project_id?: number;
      open?: boolean;
    } = {}) => {
      const qs = new URLSearchParams();
      if (params.stage_id) qs.set("stage_id", String(params.stage_id));
      if (params.organization_id) {
        qs.set("organization_id", String(params.organization_id));
      }
      if (params.project_id) qs.set("project_id", String(params.project_id));
      if (params.open) qs.set("open", "1");
      const suffix = qs.toString() ? `?${qs}` : "";
      return request<CrmDeal[]>(`/crm/deals/${suffix}`, {});
    },
    createDeal: (body: Record<string, unknown>) =>
      request<CrmDeal>("/crm/deals/", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    patchDeal: (id: number, body: Record<string, unknown>) =>
      request<CrmDeal>(`/crm/deals/${id}/`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    moveDeal: (
      id: number,
      body: { stage_id: number; position?: number; probability?: number },
    ) =>
      request<CrmDeal>(`/crm/deals/${id}/move/`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    deleteDeal: (id: number) =>
      request<void>(`/crm/deals/${id}/`, { method: "DELETE" }),
    getDealForecast: () => request<CrmDealForecast>("/crm/deals/forecast/", {}),
    listDealTasks: (dealId: number) =>
      request<CrmDealTask[]>(`/crm/deals/${dealId}/tasks/`, {}),
    createDealTask: (dealId: number, body: Record<string, unknown>) =>
      request<CrmDealTask>(`/crm/deals/${dealId}/tasks/`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    patchDealTask: (
      dealId: number,
      taskId: number,
      body: Record<string, unknown>,
    ) =>
      request<CrmDealTask>(`/crm/deals/${dealId}/tasks/${taskId}/`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    deleteDealTask: (dealId: number, taskId: number) =>
      request<void>(`/crm/deals/${dealId}/tasks/${taskId}/`, {
        method: "DELETE",
      }),

    listAutomations: () => request<CrmAutomationRule[]>("/crm/automations/", {}),
    createAutomation: (body: Record<string, unknown>) =>
      request<CrmAutomationRule>("/crm/automations/", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    patchAutomation: (id: number, body: Record<string, unknown>) =>
      request<CrmAutomationRule>(`/crm/automations/${id}/`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    deleteAutomation: (id: number) =>
      request<void>(`/crm/automations/${id}/`, { method: "DELETE" }),
    listAutomationTemplates: () =>
      request<CrmAutomationTemplate[]>("/crm/automations/templates/", {}),
    applyAutomationTemplate: (template_key: string) =>
      request<CrmAutomationRule>("/crm/automations/templates/apply/", {
        method: "POST",
        body: JSON.stringify({ template_key }),
      }),
    listAutomationRuns: () =>
      request<CrmAutomationRun[]>("/crm/automations/runs/", {}),

    getAiInsights: (stale_days = 14) =>
      request<CrmAiInsights>(`/crm/ai/insights/?stale_days=${stale_days}`, {}),
    draftAiEmail: (body: Record<string, unknown>) =>
      request<CrmAiDraftEmail>("/crm/ai/draft-email/", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    draftAiKp: (body: Record<string, unknown>) =>
      request<CrmAiDraftKp>("/crm/ai/draft-kp/", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    summarizeAiActivity: (body: Record<string, unknown>) =>
      request<CrmAiActivitySummary>("/crm/ai/activity-summary/", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    suggestAiTasks: (body: Record<string, unknown>) =>
      request<CrmAiSuggestTasks>("/crm/ai/suggest-tasks/", {
        method: "POST",
        body: JSON.stringify(body),
      }),

    listLeads: (params: { q?: string; status?: string; assigned_to?: number } = {}) => {
      const qs = new URLSearchParams();
      if (params.q) qs.set("q", params.q);
      if (params.status) qs.set("status", params.status);
      if (params.assigned_to) qs.set("assigned_to", String(params.assigned_to));
      const suffix = qs.toString() ? `?${qs}` : "";
      return request<CrmLead[]>(`/crm/leads/${suffix}`, {});
    },
    createLead: (body: Record<string, unknown>) =>
      request<CrmLead>("/crm/leads/", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    patchLead: (id: number, body: Record<string, unknown>) =>
      request<CrmLead>(`/crm/leads/${id}/`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    deleteLead: (id: number) =>
      request<void>(`/crm/leads/${id}/`, { method: "DELETE" }),
    assignLead: (
      id: number,
      body: { mode?: "manual" | "round_robin"; user_id?: number },
    ) =>
      request<CrmLead>(`/crm/leads/${id}/assign/`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    convertLead: (id: number, body: Record<string, unknown> = {}) =>
      request<{ lead: CrmLead; deal: CrmDeal }>(`/crm/leads/${id}/convert/`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    importLeads: (file: File, assign = "") => {
      const form = new FormData();
      form.append("file", file);
      if (assign) form.append("assign", assign);
      return requestForm<{
        created: number;
        skipped: number;
        duplicates: number;
        errors: string[];
      }>("/crm/leads/import/", form);
    },
  };
}

export type CrmApi = ReturnType<typeof createCrmApi>;
