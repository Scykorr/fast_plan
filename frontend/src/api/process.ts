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
};

export type CaseDefinition = {
  id: number;
  key: string;
  name: string;
  description: string;
  plan_items: Array<{ id: string; name: string; discretionary?: boolean }>;
  cmmn_xml: string;
};

export type CaseInstance = {
  id: number;
  definition: number;
  definition_name: string;
  title: string;
  status: string;
  completed_items: string[];
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
    listPacks: () => request<ProcessPack[]>("/process/packs/", {}),
    importPack: (packId: string) =>
      request<{ created: boolean; definition: ProcessDefinition }>(
        "/process/packs/import/",
        { method: "POST", body: JSON.stringify({ pack_id: packId }) },
      ),
    metrics: () => request<ProcessMetrics>("/process/metrics/", {}),
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
    closeCase: (id: number) =>
      request<CaseInstance>(`/process/cases/${id}/close/`, {
        method: "POST",
        body: "{}",
      }),
    migrateAutomation: (automationRuleId: number) =>
      request<ProcessDefinition>("/process/migrate-automation/", {
        method: "POST",
        body: JSON.stringify({ automation_rule_id: automationRuleId }),
      }),
    listDecisions: () =>
      request<Array<{ id: number; key: string; name: string; dmn_xml: string }>>(
        "/process/decisions/",
        {},
      ),
    createDecision: (body: {
      key: string;
      name: string;
      dmn_xml: string;
      decision_id: string;
    }) =>
      request("/process/decisions/", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    evaluateDecision: (id: number, inputs: Record<string, unknown>) =>
      request<{ result: unknown }>(`/process/decisions/${id}/evaluate/`, {
        method: "POST",
        body: JSON.stringify({ inputs }),
      }),
  };
}
