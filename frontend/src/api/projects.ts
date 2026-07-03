import { request } from "./client";

export type Project = {
  id: number;
  name: string;
  description: string;
  status: string;
  start_date: string | null;
  end_date: string | null;
  budget: number;
  manager: number | null;
  tracker_id: number | null;
  workflow_status_id: number | null;
  custom_values: CustomValue[];
  created_at: string;
  updated_at: string;
  wbs_count: number;
  progress: number;
  board_id: number | null;
};

export type CustomValue = {
  field_id: number;
  field_name: string;
  field_format: string;
  value: string;
};

export type ProjectCharter = {
  goals: string;
  success_criteria: string;
  constraints: string;
  assumptions: string;
  updated_at: string;
};

export type Risk = {
  id: number;
  title: string;
  description: string;
  probability: number;
  impact: number;
  score: number;
  status: string;
  mitigation: string;
  created_at: string;
  updated_at: string;
};

export type Stakeholder = {
  id: number;
  name: string;
  role: string;
  interest: number;
  influence: number;
  contact_email: string;
  notes: string;
  created_at: string;
};

export type RACIEntry = {
  id: number;
  wbs_node_id: number;
  wbs_code: string;
  wbs_title: string;
  stakeholder_id: number;
  stakeholder_name: string;
  raci_type: string;
};

export type BaselineActivity = {
  id: number;
  activity_id: number;
  wbs_code: string;
  wbs_title: string;
  start_date: string | null;
  end_date: string | null;
  duration_days: number;
  progress: number;
};

export type ProjectBaseline = {
  id: number;
  name: string;
  created_at: string;
  created_by: number | null;
  activities: BaselineActivity[];
};

export type EvmLite = {
  budget: number;
  earned_value: number;
  planned_value: number;
  actual_cost: number;
  cpi: number | null;
  spi: number | null;
  percent_complete: number;
};

export type ProjectDashboard = {
  project_id: number;
  name: string;
  status: string;
  progress: number;
  wbs_count: number;
  budget: number;
  upcoming_milestones: ScheduleActivity[];
  charter: ProjectCharter;
  top_risks: Risk[];
  evm: EvmLite;
  critical_path: {
    project_duration: number;
    critical_count: number;
    critical_path_ids: number[];
  };
};

export type WBSNode = {
  id: number;
  code: string;
  title: string;
  description: string;
  node_type: string;
  position: number;
  parent_id: number | null;
  tracker_id: number | null;
  tracker_name: string | null;
  workflow_status_id: number | null;
  workflow_status_name: string | null;
  assignee_id: number | null;
  assignee_name: string | null;
  custom_values: CustomValue[];
  schedule: ScheduleActivity | null;
  card_id: number | null;
  children: WBSNode[];
};

export type ScheduleActivity = {
  id: number;
  wbs_id: number;
  name: string;
  code: string;
  start_date: string | null;
  end_date: string | null;
  duration_days: number;
  progress: number;
  is_milestone: boolean;
};

export type ActivityDependency = {
  id: number;
  predecessor_id: number;
  successor_id: number;
  dependency_type: string;
  lag_days: number;
};

export type ProjectSchedule = {
  activities: ScheduleActivity[];
  dependencies: ActivityDependency[];
};

export type CriticalPathActivity = {
  id: number;
  wbs_id: number;
  code: string;
  name: string;
  duration_days: number;
  early_start: number;
  early_finish: number;
  late_start: number;
  late_finish: number;
  slack: number;
  is_critical: boolean;
};

export type CriticalPath = {
  activities: CriticalPathActivity[];
  critical_path_ids: number[];
  project_duration: number;
};

export type ProjectCalendarEvent = {
  id: string;
  title: string;
  start: string;
  allDay: boolean;
  extendedProps: {
    activity_id: number;
    project_id: number;
    project_name: string;
    wbs_code: string;
    event_type: "milestone";
  };
};

export type ProjectPatchBody = {
  name?: string;
  description?: string;
  status?: string;
  start_date?: string | null;
  end_date?: string | null;
  budget?: number;
  manager?: number | null;
  tracker_id?: number | null;
  workflow_status_id?: number | null;
  custom_values?: Record<string, string>;
};

export function createProjectsApi(token: string) {
  return {
    getProjects: () => request<Project[]>("/projects/", {}, token),

    createProject: (body: {
      name: string;
      description?: string;
      status?: string;
      start_date?: string;
      end_date?: string;
      budget?: number;
    }) =>
      request<Project>("/projects/", {
        method: "POST",
        body: JSON.stringify(body),
      }, token),

    getProject: (id: number) =>
      request<Project>(`/projects/${id}/`, {}, token),

    patchProject: (id: number, body: ProjectPatchBody) =>
      request<Project>(`/projects/${id}/`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }, token),

    getDashboard: (id: number) =>
      request<ProjectDashboard>(`/projects/${id}/dashboard/`, {}, token),

    getWBS: (projectId: number) =>
      request<WBSNode[]>(`/projects/${projectId}/wbs/`, {}, token),

    createWBSNode: (
      projectId: number,
      body: {
        title: string;
        parent_id: number;
        node_type?: string;
        description?: string;
      },
    ) =>
      request<WBSNode[]>(`/projects/${projectId}/wbs/`, {
        method: "POST",
        body: JSON.stringify(body),
      }, token),

    updateWBSNode: (
      wbsId: number,
      body: {
        title?: string;
        description?: string;
        parent_id?: number;
        position?: number;
        tracker_id?: number | null;
        workflow_status_id?: number | null;
        assignee_id?: number | null;
        custom_values?: Record<string, string>;
      },
    ) =>
      request<WBSNode[]>(`/wbs/${wbsId}/`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }, token),

    deleteWBSNode: (wbsId: number) =>
      request<void>(`/wbs/${wbsId}/`, { method: "DELETE" }, token),

    getSchedule: (projectId: number) =>
      request<ProjectSchedule>(`/projects/${projectId}/schedule/`, {}, token),

    updateActivity: (
      activityId: number,
      body: Partial<ScheduleActivity>,
    ) =>
      request<ScheduleActivity>(`/activities/${activityId}/`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }, token),

    getProjectCalendar: (projectId: number, year: number, month: number) =>
      request<ProjectCalendarEvent[]>(
        `/projects/${projectId}/calendar/?year=${year}&month=${month}`,
        {},
        token,
      ),

    getRisks: (projectId: number) =>
      request<Risk[]>(`/projects/${projectId}/risks/`, {}, token),

    createRisk: (projectId: number, body: Partial<Risk>) =>
      request<Risk>(`/projects/${projectId}/risks/`, {
        method: "POST",
        body: JSON.stringify(body),
      }, token),

    deleteRisk: (riskId: number) =>
      request<void>(`/risks/${riskId}/`, { method: "DELETE" }, token),

    getStakeholders: (projectId: number) =>
      request<Stakeholder[]>(`/projects/${projectId}/stakeholders/`, {}, token),

    createStakeholder: (projectId: number, body: Partial<Stakeholder>) =>
      request<Stakeholder>(`/projects/${projectId}/stakeholders/`, {
        method: "POST",
        body: JSON.stringify(body),
      }, token),

    deleteStakeholder: (id: number) =>
      request<void>(`/stakeholders/${id}/`, { method: "DELETE" }, token),

    getCharter: (projectId: number) =>
      request<ProjectCharter>(`/projects/${projectId}/charter/`, {}, token),

    patchCharter: (projectId: number, body: Partial<ProjectCharter>) =>
      request<ProjectCharter>(`/projects/${projectId}/charter/`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }, token),

    getRACI: (projectId: number) =>
      request<RACIEntry[]>(`/projects/${projectId}/raci/`, {}, token),

    createRACI: (
      projectId: number,
      body: { wbs_node_id: number; stakeholder_id: number; raci_type: string },
    ) =>
      request<RACIEntry>(`/projects/${projectId}/raci/`, {
        method: "POST",
        body: JSON.stringify(body),
      }, token),

    deleteRACI: (id: number) =>
      request<void>(`/raci/${id}/`, { method: "DELETE" }, token),

    getBaselines: (projectId: number) =>
      request<ProjectBaseline[]>(`/projects/${projectId}/baselines/`, {}, token),

    createBaseline: (projectId: number, name?: string) =>
      request<ProjectBaseline>(`/projects/${projectId}/baselines/`, {
        method: "POST",
        body: JSON.stringify({ name }),
      }, token),

    getCriticalPath: (projectId: number) =>
      request<CriticalPath>(`/projects/${projectId}/critical-path/`, {}, token),

    exportProject: (projectId: number) =>
      request<Record<string, unknown>>(`/projects/${projectId}/export/`, {}, token),
  };
}
