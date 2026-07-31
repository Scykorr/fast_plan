import { request } from "./client";

export type ProcessDefinition = {
  id: number;
  key: string;
  name: string;
  description: string;
  bpmn_xml: string;
  process_id: string;
  version: number;
  is_published: boolean;
  category: string;
  created_at: string;
  updated_at: string;
};

export type ProcessInstance = {
  id: number;
  deployment: number;
  definition_name: string;
  definition_key: string;
  business_key: string;
  deal: number | null;
  project: number | null;
  organization: number | null;
  status: string;
  data: Record<string, unknown>;
  error_message: string;
  started_at: string;
  completed_at: string | null;
};

export type ProcessUserTask = {
  id: number;
  instance_id: number;
  definition_name: string;
  name: string;
  description: string;
  status: string;
  assignee: number | null;
  candidate_role: string;
  form_schema: Record<string, unknown>;
  form_data: Record<string, unknown>;
  due_at: string | null;
  created_at: string;
  completed_at: string | null;
  deal: number | null;
  project: number | null;
  wbs_node: number | null;
  wbs_code: string | null;
  wbs_title: string | null;
};

export type CasePlanItem = {
  id: string;
  name: string;
  discretionary?: boolean;
  required?: boolean;
  depends_on?: string[];
  process_key?: string;
  enabled?: boolean;
};

export type CaseDefinition = {
  id: number;
  key: string;
  name: string;
  description: string;
  plan_items: CasePlanItem[];
  cmmn_xml: string;
};

export type CaseInstance = {
  id: number;
  definition: number;
  definition_name: string;
  title: string;
  status: string;
  completed_items: string[];
  available_items: CasePlanItem[];
  required_incomplete: string[];
  deal?: number | null;
  project?: number | null;
  started_at: string;
  closed_at: string | null;
};

export type ProcessPack = {
  id: string;
  name: string;
  filename: string;
  readme: string;
};

export type ProcessMetrics = {
  instance_count: number;
  active_count: number;
  completed_count: number;
  error_count: number;
  open_user_tasks: number;
  overdue_user_tasks: number;
  avg_cycle_hours: number | null;
  by_status: Record<string, number>;
};

export type ProcessOpsRow = {
  id: number;
  name?: string;
  definition_name?: string;
  business_key?: string;
  status?: string;
  error_message?: string;
  started_at?: string | null;
  created_at?: string | null;
  due_at?: string | null;
  age_hours?: number | null;
  overdue_hours?: number | null;
  instance_id?: number;
  deal?: number | null;
  project?: number | null;
  reasons?: string[];
};

export type ProcessOps = {
  thresholds: { stuck_hours: number; aging_hours: number };
  stuck_instances: ProcessOpsRow[];
  aging_tasks: ProcessOpsRow[];
  sla_breaches: ProcessOpsRow[];
  counts: {
    stuck_instances: number;
    aging_tasks: number;
    sla_breaches: number;
    open_user_tasks: number;
  };
};

export type ProcessMining = {
  instance_sample: number;
  event_count: number;
  dfg: Array<{ from: string; to: string; count: number }>;
  top_paths: Array<{ path: string[]; count: number }>;
  bottlenecks: Array<{ node: string; avg_hours: number; samples: number }>;
};

export type ProcessAdapterParam = {
  name: string;
  type: string;
  required?: boolean;
};

export type ProcessAdapterCatalogItem = {
  operation: string;
  label: string;
  description: string;
  params: ProcessAdapterParam[];
};

export type ProcessExecutableElement = {
  type: string;
  status: string;
  note?: string;
};

export type ProcessAdapterCatalog = {
  adapters: ProcessAdapterCatalogItem[];
  executable_elements: ProcessExecutableElement[];
  dispatch_hint: string;
};

export type DecisionDefinition = {
  id: number;
  key: string;
  name: string;
  dmn_xml: string;
  decision_id?: string;
};

export function createProcessApi() {
  return {
    listDefinitions: () =>
      request<ProcessDefinition[]>("/process/definitions/", {}),
    createDefinition: (body: Partial<ProcessDefinition>) =>
      request<ProcessDefinition>("/process/definitions/", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    getDefinition: (id: number) =>
      request<ProcessDefinition>(`/process/definitions/${id}/`, {}),
    patchDefinition: (id: number, body: Partial<ProcessDefinition>) =>
      request<ProcessDefinition>(`/process/definitions/${id}/`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    publish: (id: number) =>
      request<{ definition: ProcessDefinition; deployment_id: number }>(
        `/process/definitions/${id}/publish/`,
        { method: "POST", body: "{}" },
      ),
    start: (id: number, body: Record<string, unknown> = {}) =>
      request<ProcessInstance>(`/process/definitions/${id}/start/`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    exportDefinition: (id: number) =>
      request<{ bpmn_xml: string; key: string; name: string }>(
        `/process/definitions/${id}/export/`,
        {},
      ),
    listInstances: () =>
      request<ProcessInstance[]>("/process/instances/", {}),
    getInstance: (id: number) =>
      request<{
        instance: ProcessInstance;
        user_tasks: ProcessUserTask[];
        bpmn_xml: string;
        active_element_ids: string[];
      }>(`/process/instances/${id}/`, {}),
    listTasks: (params?: { status?: string; mine?: boolean }) => {
      const q = new URLSearchParams();
      if (params?.status) q.set("status", params.status);
      if (params?.mine) q.set("mine", "true");
      const suffix = q.toString() ? `?${q}` : "";
      return request<ProcessUserTask[]>(`/process/tasks/${suffix}`, {});
    },
    completeTask: (id: number, formData: Record<string, unknown> = {}) =>
      request<{ task: ProcessUserTask; instance: ProcessInstance }>(
        `/process/tasks/${id}/complete/`,
        {
          method: "POST",
          body: JSON.stringify({ form_data: formData, ...formData }),
        },
      ),
    bindTask: (id: number, wbsNodeId: number | null) =>
      request<ProcessUserTask>(`/process/tasks/${id}/bind/`, {
        method: "PATCH",
        body: JSON.stringify({ wbs_node_id: wbsNodeId }),
      }),
    listPacks: () => request<ProcessPack[]>("/process/packs/", {}),
    importPack: (packId: string) =>
      request<{ created: boolean; definition: ProcessDefinition }>(
        "/process/packs/import/",
        { method: "POST", body: JSON.stringify({ pack_id: packId }) },
      ),
    metrics: () => request<ProcessMetrics>("/process/metrics/", {}),
    ops: (params: { stuck_hours?: number; aging_hours?: number } = {}) => {
      const qs = new URLSearchParams();
      if (params.stuck_hours != null) qs.set("stuck_hours", String(params.stuck_hours));
      if (params.aging_hours != null) qs.set("aging_hours", String(params.aging_hours));
      const suffix = qs.toString() ? `?${qs}` : "";
      return request<ProcessOps>(`/process/ops/${suffix}`, {});
    },
    mining: () => request<ProcessMining>("/process/mining/", {}),
    listCaseDefinitions: () =>
      request<CaseDefinition[]>("/process/cases/definitions/", {}),
    createCaseDefinition: (body: Partial<CaseDefinition>) =>
      request<CaseDefinition>("/process/cases/definitions/", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    listCases: () => request<CaseInstance[]>("/process/cases/", {}),
    startCase: (body: {
      definition_id: number;
      title?: string;
      deal_id?: number;
      project_id?: number;
    }) =>
      request<CaseInstance>("/process/cases/", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    completeCaseItem: (id: number, itemId: string) =>
      request<CaseInstance>(`/process/cases/${id}/complete-item/`, {
        method: "POST",
        body: JSON.stringify({ item_id: itemId }),
      }),
    closeCase: (id: number, force = false) =>
      request<CaseInstance>(`/process/cases/${id}/close/`, {
        method: "POST",
        body: JSON.stringify({ force }),
      }),
    migrateAutomation: (automationRuleId: number) =>
      request<ProcessDefinition>("/process/migrate-automation/", {
        method: "POST",
        body: JSON.stringify({ automation_rule_id: automationRuleId }),
      }),
    listDecisions: () =>
      request<DecisionDefinition[]>("/process/decisions/", {}),
    createDecision: (body: {
      key: string;
      name: string;
      dmn_xml: string;
      decision_id: string;
    }) =>
      request<DecisionDefinition>("/process/decisions/", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    evaluateDecision: (id: number, inputs: Record<string, unknown>) =>
      request<{ result: unknown }>(`/process/decisions/${id}/evaluate/`, {
        method: "POST",
        body: JSON.stringify({ inputs }),
      }),
    adaptersCatalog: () =>
      request<ProcessAdapterCatalog>("/process/adapters/", {}),
  };
}
