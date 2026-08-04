import { request, requestBlob, requestForm } from "./client";
import type { Project } from "./projects";

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

export type CrmPersonDuplicateGroup = {
  reason: string;
  key: string;
  survivor_id: number;
  source_id: number;
  people: Array<{
    id: number;
    full_name: string;
    email: string;
    phone: string;
  }>;
};

export type CrmOrgDuplicateGroup = {
  reason: string;
  key: string;
  survivor_id: number;
  source_id: number;
  organizations: Array<{
    id: number;
    name: string;
    website: string;
    industry: string;
  }>;
};

export type CrmActivityKind =
  | "call"
  | "meeting"
  | "email"
  | "telegram"
  | "instagram"
  | "vk"
  | "note"
  | "invoice"
  | "order"
  | "other";

export type CrmActivity = {
  id: number;
  kind: CrmActivityKind;
  channel: "manual" | "email" | "telegram" | "other" | string;
  direction: "inbound" | "outbound" | "internal" | string;
  external_id: string;
  subject: string;
  body: string;
  occurred_at: string;
  person: number | null;
  person_name: string | null;
  organization: number | null;
  organization_name: string | null;
  deal: number | null;
  project: number | null;
  project_name: string | null;
  created_by: number | null;
  created_by_email: string | null;
  created_at: string;
};

export type CrmChannelConnection = {
  id: number;
  provider: "imap" | "telegram" | string;
  name: string;
  is_active: boolean;
  config: Record<string, unknown>;
  last_synced_at: string | null;
  last_error: string;
  created_at: string;
  updated_at: string;
};

export type CrmIntegrationConnector = {
  id: number;
  provider: "stripe" | "onec" | "whatsapp" | "sms" | string;
  name: string;
  is_active: boolean;
  config_public: Record<string, unknown>;
  webhook_token: string;
  webhook_path: string;
  last_synced_at: string | null;
  last_error: string;
  created_at: string;
  updated_at: string;
};

export type CrmConnectorCatalogItem = {
  provider: string;
  label: string;
  config_keys: string[];
  supports_sync: boolean;
  supports_webhook: boolean;
  supports_send?: boolean;
};

export type CrmDocument = {
  id: number;
  doc_type: "quote" | "invoice" | "contract" | string;
  number: string;
  title: string;
  status: string;
  amount: number | string;
  currency: string;
  body: string;
  line_items: Array<Record<string, unknown>>;
  issue_date: string | null;
  due_date: string | null;
  renewal_date?: string | null;
  term_months?: number | null;
  arr_annual?: number | string | null;
  organization: number | null;
  organization_name: string | null;
  person: number | null;
  person_name: string | null;
  deal: number | null;
  deal_title: string | null;
  project: number | null;
  pdf_url: string | null;
  paid_total: number;
  stock_fulfilled?: boolean;
  created_at: string;
  updated_at: string;
};

export type CrmRenewalsSummary = {
  workspace_id: number;
  as_of: string;
  within_days: number;
  arr_total: string;
  contract_count: number;
  upcoming: Array<{
    id: number;
    title: string;
    number: string;
    status: string;
    amount: string;
    arr_annual: string;
    renewal_date: string;
    term_months: number | null;
    organization_id: number | null;
    organization_name: string | null;
    deal_id?: number | null;
    days_until: number;
  }>;
};

export type CrmDocumentShareLink = {
  id: number;
  token: string;
  label: string;
  created_at: string;
  expires_at: string | null;
  last_accessed_at: string | null;
  is_active: boolean;
  allow_approve: boolean;
  allow_pdf: boolean;
  url_path: string;
};

export type PublicCrmDocumentShare = {
  share: {
    label: string;
    allow_approve: boolean;
    allow_pdf: boolean;
    workspace_name: string;
  };
  document: {
    id: number;
    doc_type: string;
    number: string;
    title: string;
    status: string;
    amount: string;
    currency: string;
    body: string;
    line_items: Array<Record<string, unknown>>;
    issue_date: string | null;
    due_date: string | null;
    organization_name: string | null;
    person_name: string | null;
    paid_total: string;
    balance_due: string;
    payment_status: "unpaid" | "partial" | "paid" | string;
    payments: Array<{
      amount: string;
      paid_at: string;
      currency: string;
    }>;
    can_approve: boolean;
  };
};

export type CrmSku = {
  id: number;
  code: string;
  name: string;
  unit: string;
  unit_price: number | string;
  qty_on_hand: number | string;
  is_active: boolean;
  notes: string;
  external_ref?: string;
  created_at: string;
  updated_at: string;
};

export type CrmAnalytics = {
  leads: {
    total: number;
    converted: number;
    conversion_rate: number;
    by_source: Array<{
      source: string;
      total: number;
      converted: number;
      conversion_rate: number;
    }>;
  };
  deals: {
    open_count: number;
    won_count: number;
    lost_count: number;
    won_amount: number;
    avg_check: number;
    forecast_amount: number;
    by_owner: Array<{
      owner_id: number | null;
      owner_email: string | null;
      open_count: number;
      won_count: number;
      won_amount: number;
    }>;
  };
  finance: {
    income_total: number;
    expense_total: number;
    cac: number | null;
    ltv: number | null;
  };
};

export type CrmArAp = {
  ar_open_amount: number;
  ar_open_count: number;
  invoices_paid_amount: number;
  invoices_total_count: number;
  open_invoices: Array<{
    id: number;
    number: string;
    title: string;
    amount: number;
    due_date: string | null;
    status: string;
    organization_name: string | null;
    deal_id?: number | null;
  }>;
  ap_open_amount: number;
  ap_open_count: number;
  bills_paid_amount: number;
  bills_total_count: number;
  expense_ledger_amount: number;
  open_bills: Array<{
    id: number;
    number: string;
    title: string;
    amount: number;
    due_date: string | null;
    status: string;
    organization_name: string | null;
    deal_id?: number | null;
  }>;
};

export type CrmPnl = {
  organization_id: number | null;
  deal_id: number | null;
  income_total: number;
  expense_total: number;
  profit: number;
  by_organization: Array<{
    organization_id: number;
    organization_name: string;
    income: number;
    expense: number;
    profit: number;
  }>;
  by_deal: Array<{
    deal_id: number;
    deal_title: string;
    income: number;
    expense: number;
    profit: number;
  }>;
};

export type CrmCashflowForecast = {
  as_of: string;
  horizon_days: number;
  buckets: Array<{
    label: string;
    days: number;
    inflow: number;
    outflow: number;
    deal_forecast: number;
    net: number;
  }>;
  schedule: Array<{
    kind: string;
    source: string;
    id: number;
    title: string;
    amount: number;
    due_date: string | null;
    organization_name: string | null;
  }>;
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
  person_phone?: string | null;
  project: number | null;
  project_name: string | null;
  owner: number | null;
  owner_email: string | null;
  position: number;
  notes: string;
  is_open: boolean;
  open_tasks_count?: number;
  bant_budget?: boolean;
  bant_authority?: boolean;
  bant_need?: boolean;
  bant_timeline?: boolean;
  qualification_notes?: string;
  qualification_score?: number;
  playbook_done?: string[];
  stage_playbook?: string[];
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

export type CrmTaskPriority = "low" | "normal" | "high" | "urgent";
export type CrmTaskBoardStatus = "todo" | "doing" | "done";
export type CrmTaskRepeat = "none" | "daily" | "weekly" | "monthly";

export type CrmChecklistItem = {
  id: string;
  text: string;
  done: boolean;
};

export type CrmDealTask = {
  id: number;
  deal: number;
  title: string;
  due_date: string | null;
  is_done: boolean;
  priority: CrmTaskPriority;
  board_status: CrmTaskBoardStatus;
  checklist: CrmChecklistItem[];
  checklist_done?: number;
  checklist_total?: number;
  repeat: CrmTaskRepeat;
  assignee: number | null;
  assignee_email: string | null;
  remind_before_days: number;
  notes: string;
  created_at: string;
  updated_at: string;
};

export type CrmLeadTask = {
  id: number;
  lead: number;
  title: string;
  due_date: string | null;
  is_done: boolean;
  priority: CrmTaskPriority;
  board_status: CrmTaskBoardStatus;
  checklist: CrmChecklistItem[];
  checklist_done?: number;
  checklist_total?: number;
  repeat: CrmTaskRepeat;
  assignee: number | null;
  assignee_email: string | null;
  remind_before_days: number;
  notes: string;
  created_at: string;
  updated_at: string;
};

export type CrmBoardTask = {
  kind: "deal" | "lead";
  id: number;
  title: string;
  due_date: string | null;
  is_done: boolean;
  priority: CrmTaskPriority;
  board_status: CrmTaskBoardStatus;
  checklist: CrmChecklistItem[];
  repeat: CrmTaskRepeat;
  assignee: number | null;
  assignee_email: string | null;
  deal_id: number | null;
  deal_title: string | null;
  lead_id: number | null;
  lead_name: string | null;
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
  | "activity.created"
  | "document.accepted"
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
    listOrganizationDuplicates: () =>
      request<{ workspace_id: number; groups: CrmOrgDuplicateGroup[] }>(
        "/crm/organizations/duplicates/",
        {},
      ),
    mergeOrganization: (survivorId: number, sourceId: number) =>
      request<CrmOrganization>(`/crm/organizations/${survivorId}/merge/`, {
        method: "POST",
        body: JSON.stringify({ source_id: sourceId }),
      }),
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
    listPersonDuplicates: () =>
      request<{ workspace_id: number; groups: CrmPersonDuplicateGroup[] }>(
        "/crm/people/duplicates/",
        {},
      ),
    mergePerson: (survivorId: number, sourceId: number) =>
      request<CrmPerson>(`/crm/people/${survivorId}/merge/`, {
        method: "POST",
        body: JSON.stringify({ source_id: sourceId }),
      }),
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
    spawnFromActivity: (
      activityId: number,
      body: {
        mode: "wbs" | "process";
        project_id?: number;
        parent_wbs_id?: number;
        process_key?: string;
      },
    ) =>
      request<{
        mode: string;
        wbs_node_id?: number;
        project_id?: number;
        instance_id?: number;
        definition_key?: string;
      }>(`/crm/activities/${activityId}/spawn/`, {
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
    createProjectFromDeal: (
      id: number,
      body: { template_id?: number | null; require_won?: boolean } = {},
    ) =>
      request<{ deal: CrmDeal; project: Project }>(
        `/crm/deals/${id}/create-project/`,
        {
          method: "POST",
          body: JSON.stringify(body),
        },
      ),
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

    listLeadTasks: (leadId: number) =>
      request<CrmLeadTask[]>(`/crm/leads/${leadId}/tasks/`, {}),
    createLeadTask: (leadId: number, body: Record<string, unknown>) =>
      request<CrmLeadTask>(`/crm/leads/${leadId}/tasks/`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    patchLeadTask: (
      leadId: number,
      taskId: number,
      body: Record<string, unknown>,
    ) =>
      request<CrmLeadTask>(`/crm/leads/${leadId}/tasks/${taskId}/`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    deleteLeadTask: (leadId: number, taskId: number) =>
      request<void>(`/crm/leads/${leadId}/tasks/${taskId}/`, {
        method: "DELETE",
      }),

    listCrmTaskBoard: (params?: {
      board_status?: string;
      kind?: "deal" | "lead";
      include_done?: boolean;
    }) => {
      const query = new URLSearchParams();
      if (params?.board_status) query.set("board_status", params.board_status);
      if (params?.kind) query.set("kind", params.kind);
      if (params?.include_done) query.set("include_done", "1");
      const suffix = query.toString() ? `?${query}` : "";
      return request<{ results: CrmBoardTask[]; count: number }>(
        `/crm/tasks/board/${suffix}`,
        {},
      );
    },
    moveCrmBoardTask: (
      kind: "deal" | "lead",
      taskId: number,
      board_status: CrmTaskBoardStatus,
    ) =>
      request<CrmBoardTask>(`/crm/tasks/board/${kind}/${taskId}/`, {
        method: "PATCH",
        body: JSON.stringify({ board_status }),
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

    listChannels: () => request<CrmChannelConnection[]>("/crm/channels/", {}),
    createChannel: (body: Record<string, unknown>) =>
      request<CrmChannelConnection>("/crm/channels/", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    patchChannel: (id: number, body: Record<string, unknown>) =>
      request<CrmChannelConnection>(`/crm/channels/${id}/`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    deleteChannel: (id: number) =>
      request<void>(`/crm/channels/${id}/`, { method: "DELETE" }),
    syncChannel: (id: number) =>
      request<{ ok: boolean; created: number; connection: CrmChannelConnection }>(
        `/crm/channels/${id}/sync/`,
        { method: "POST", body: "{}" },
      ),

    listConnectorCatalog: () =>
      request<{ providers: CrmConnectorCatalogItem[] }>(
        "/crm/connectors/catalog/",
        {},
      ),
    listConnectors: () =>
      request<CrmIntegrationConnector[]>("/crm/connectors/", {}),
    createConnector: (body: Record<string, unknown>) =>
      request<CrmIntegrationConnector>("/crm/connectors/", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    patchConnector: (id: number, body: Record<string, unknown>) =>
      request<CrmIntegrationConnector>(`/crm/connectors/${id}/`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    deleteConnector: (id: number) =>
      request<void>(`/crm/connectors/${id}/`, { method: "DELETE" }),
    syncConnector: (id: number) =>
      request<{ ok: boolean; created?: number; connector: CrmIntegrationConnector }>(
        `/crm/connectors/${id}/sync/`,
        { method: "POST", body: "{}" },
      ),
    sendConnectorSms: (id: number, body: { to: string; body: string }) =>
      request<{ ok: boolean; sent: boolean }>(`/crm/connectors/${id}/send/`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    sendConnectorDial: (
      id: number,
      body: {
        to: string;
        note?: string;
        person_id?: number;
        deal_id?: number;
        lead_id?: number;
      },
    ) =>
      request<{ ok: boolean; dialed?: boolean; remote?: boolean; pbx?: string }>(
        `/crm/connectors/${id}/send/`,
        {
          method: "POST",
          body: JSON.stringify(body),
        },
      ),
    getConnectorAriBridge: (id: number) =>
      request<{
        ok: boolean;
        ready?: boolean;
        command?: string;
        hint?: string;
        detail?: string;
        ws_url?: string;
      }>(`/crm/connectors/${id}/ari-bridge/`, {}),

    listDocuments: (params: { doc_type?: string; status?: string } = {}) => {
      const qs = new URLSearchParams();
      if (params.doc_type) qs.set("doc_type", params.doc_type);
      if (params.status) qs.set("status", params.status);
      const suffix = qs.toString() ? `?${qs}` : "";
      return request<CrmDocument[]>(`/crm/documents/${suffix}`, {});
    },
    listSkus: (params: { q?: string; active?: "0" | "1" } = {}) => {
      const qs = new URLSearchParams();
      if (params.q) qs.set("q", params.q);
      if (params.active) qs.set("active", params.active);
      const suffix = qs.toString() ? `?${qs}` : "";
      return request<CrmSku[]>(`/crm/skus/${suffix}`, {});
    },
    createSku: (body: Record<string, unknown>) =>
      request<CrmSku>("/crm/skus/", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    patchSku: (id: number, body: Record<string, unknown>) =>
      request<CrmSku>(`/crm/skus/${id}/`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    deleteSku: (id: number) =>
      request<void>(`/crm/skus/${id}/`, { method: "DELETE" }),
    adjustSku: (id: number, body: Record<string, unknown>) =>
      request<CrmSku>(`/crm/skus/${id}/adjust/`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    createDocument: (body: Record<string, unknown>) =>
      request<CrmDocument>("/crm/documents/", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    patchDocument: (id: number, body: Record<string, unknown>) =>
      request<CrmDocument>(`/crm/documents/${id}/`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    deleteDocument: (id: number) =>
      request<void>(`/crm/documents/${id}/`, { method: "DELETE" }),
    renderDocumentPdf: (id: number) =>
      request<CrmDocument>(`/crm/documents/${id}/pdf/`, {
        method: "POST",
        body: "{}",
      }),
    createDocumentPayment: (id: number, body: Record<string, unknown>) =>
      request<Record<string, unknown>>(`/crm/documents/${id}/payments/`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    listDocumentShareLinks: (documentId: number) =>
      request<CrmDocumentShareLink[]>(
        `/crm/documents/${documentId}/share-links/`,
        {},
      ),
    createDocumentShareLink: (
      documentId: number,
      body: {
        label?: string;
        allow_approve?: boolean;
        allow_pdf?: boolean;
        expires_at?: string | null;
      } = {},
    ) =>
      request<CrmDocumentShareLink>(
        `/crm/documents/${documentId}/share-links/`,
        {
          method: "POST",
          body: JSON.stringify(body),
        },
      ),
    revokeDocumentShareLink: (documentId: number, linkId: number) =>
      request<void>(`/crm/documents/${documentId}/share-links/${linkId}/`, {
        method: "DELETE",
      }),
    getArAp: () => request<CrmArAp>("/crm/ar-ap/", {}),
    getRenewals: (withinDays = 90) =>
      request<CrmRenewalsSummary>(
        `/crm/renewals/?within_days=${withinDays}`,
        {},
      ),
    remindRenewals: (body: { within_days?: number; dry_run?: boolean } = {}) =>
      request<{
        created_tasks: number;
        created_notifications: number;
        skipped: number;
        within_days: number;
        dry_run: boolean;
        items: Array<Record<string, unknown>>;
      }>("/crm/renewals/", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    getPnl: (params?: { organization_id?: number; deal_id?: number }) => {
      const query = new URLSearchParams();
      if (params?.organization_id) {
        query.set("organization_id", String(params.organization_id));
      }
      if (params?.deal_id) {
        query.set("deal_id", String(params.deal_id));
      }
      const suffix = query.toString() ? `?${query}` : "";
      return request<CrmPnl>(`/crm/finance/pnl/${suffix}`, {});
    },
    getCashflowForecast: (days = 90) =>
      request<CrmCashflowForecast>(`/crm/cashflow-forecast/?days=${days}`, {}),
    getAnalytics: () => request<CrmAnalytics>("/crm/analytics/", {}),
    listSavedReports: () =>
      request<Array<{ id: number; name: string; query: Record<string, unknown> }>>(
        "/crm/saved-reports/",
        {},
      ),
    createSavedReport: (body: Record<string, unknown>) =>
      request<{ id: number; name: string; query: Record<string, unknown> }>(
        "/crm/saved-reports/",
        { method: "POST", body: JSON.stringify(body) },
      ),
    deleteSavedReport: (id: number) =>
      request<void>(`/crm/saved-reports/${id}/`, { method: "DELETE" }),
    runReport: ((
      query: Record<string, unknown>,
      format?: "json" | "csv",
    ) => {
      if (format === "csv") {
        return requestBlob("/crm/reports/run/?export=csv", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query, format: "csv" }),
        });
      }
      return request<Record<string, unknown>>("/crm/reports/run/", {
        method: "POST",
        body: JSON.stringify({ query }),
      });
    }) as {
      (query: Record<string, unknown>, format: "csv"): Promise<Blob>;
      (
        query: Record<string, unknown>,
        format?: "json",
      ): Promise<Record<string, unknown>>;
    },
    listSavedFilters: (target?: string) => {
      const q = target ? `?target=${encodeURIComponent(target)}` : "";
      return request<
        Array<{
          id: number;
          target: string;
          name: string;
          params: Record<string, unknown>;
        }>
      >(`/crm/saved-filters/${q}`, {});
    },
    createSavedFilter: (body: {
      target: string;
      name: string;
      params?: Record<string, unknown>;
    }) =>
      request<{
        id: number;
        target: string;
        name: string;
        params: Record<string, unknown>;
      }>("/crm/saved-filters/", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    deleteSavedFilter: (id: number) =>
      request<void>(`/crm/saved-filters/${id}/`, { method: "DELETE" }),
    listCustomFields: (target?: string) => {
      const q = target ? `?target=${encodeURIComponent(target)}` : "";
      return request<
        Array<{
          id: number;
          target: string;
          key: string;
          label: string;
          field_type: string;
          options: string[];
          required: boolean;
          position: number;
          is_active: boolean;
        }>
      >(`/crm/custom-fields/${q}`, {});
    },
    createCustomField: (body: {
      target: string;
      key: string;
      label: string;
      field_type?: string;
      options?: string[];
      required?: boolean;
      position?: number;
    }) =>
      request<{
        id: number;
        target: string;
        key: string;
        label: string;
        field_type: string;
        options: string[];
        required: boolean;
        position: number;
        is_active: boolean;
      }>("/crm/custom-fields/", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    deleteCustomField: (id: number) =>
      request<void>(`/crm/custom-fields/${id}/`, { method: "DELETE" }),
    getEntityCustomFields: (
      target: "organization" | "person" | "deal" | "lead",
      entityId: number,
    ) =>
      request<{
        target: string;
        entity_id: number;
        values: Record<string, unknown>;
        definitions: Array<{
          id: number;
          target: string;
          key: string;
          label: string;
          field_type: string;
          options: string[];
          required: boolean;
          position: number;
          is_active: boolean;
        }>;
      }>(`/crm/${target}/${entityId}/custom-fields/`, {}),
    putEntityCustomFields: (
      target: "organization" | "person" | "deal" | "lead",
      entityId: number,
      values: Record<string, unknown>,
    ) =>
      request<{
        target: string;
        entity_id: number;
        values: Record<string, unknown>;
      }>(`/crm/${target}/${entityId}/custom-fields/`, {
        method: "PUT",
        body: JSON.stringify({ values }),
      }),
    graphql: (query: string) =>
      request<{ data: Record<string, unknown> }>("/crm/graphql/", {
        method: "POST",
        body: JSON.stringify({ query }),
      }),
  };
}

export type CrmApi = ReturnType<typeof createCrmApi>;

const API_BASE = "/api";

export async function fetchPublicCrmDocumentShare(
  token: string,
): Promise<PublicCrmDocumentShare> {
  const response = await fetch(`${API_BASE}/crm/share/${token}/`);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || "Share link not found");
  }
  return response.json();
}

export async function approvePublicCrmDocument(
  token: string,
): Promise<PublicCrmDocumentShare> {
  const response = await fetch(`${API_BASE}/crm/share/${token}/approve/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  });
  if (!response.ok) {
    let message = "Approve failed";
    try {
      const data = await response.json();
      message = data.detail || JSON.stringify(data);
    } catch {
      /* ignore */
    }
    throw new Error(message);
  }
  return response.json();
}

export function publicCrmDocumentPdfUrl(token: string): string {
  return `${API_BASE}/crm/share/${token}/pdf/`;
}
