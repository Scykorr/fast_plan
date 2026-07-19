import { request, requestBlob } from "./client";

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

export type ProjectStatusReport = {
  project: {
    id: number;
    name: string;
    status: string;
    budget: number;
    start_date: string | null;
    end_date: string | null;
    description?: string;
  };
  charter: ProjectCharter;
  progress: number;
  evm: EvmLite;
  critical_path: CriticalPath;
  top_risks: Risk[];
  stakeholders: Stakeholder[];
  milestones: ScheduleActivity[];
  generated_at: string;
};

export type WorkItemComment = {
  id: number;
  kind: "comment" | "decision";
  body: string;
  author: number;
  author_name: string;
  wbs_node_id: number | null;
  card_id: number | null;
  created_at: string;
  updated_at: string;
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

export function createProjectsApi() {
  return {
    getProjects: () => request<Project[]>("/projects/", {}),

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
      }),

    getProject: (id: number) =>
      request<Project>(`/projects/${id}/`, {}),

    patchProject: (id: number, body: ProjectPatchBody) =>
      request<Project>(`/projects/${id}/`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),

    getDashboard: (id: number) =>
      request<ProjectDashboard>(`/projects/${id}/dashboard/`, {}),

    getWBS: (projectId: number) =>
      request<WBSNode[]>(`/projects/${projectId}/wbs/`, {}),

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
      }),

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
      }),

    deleteWBSNode: (wbsId: number) =>
      request<void>(`/wbs/${wbsId}/`, { method: "DELETE" }),

    getSchedule: (projectId: number) =>
      request<ProjectSchedule>(`/projects/${projectId}/schedule/`, {}),

    updateActivity: (
      activityId: number,
      body: Partial<ScheduleActivity>,
    ) =>
      request<ScheduleActivity>(`/activities/${activityId}/`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),

    getProjectCalendar: (projectId: number, year: number, month: number) =>
      request<ProjectCalendarEvent[]>(
        `/projects/${projectId}/calendar/?year=${year}&month=${month}`,
        {}
      ),

    getRisks: (projectId: number) =>
      request<Risk[]>(`/projects/${projectId}/risks/`, {}),

    createRisk: (projectId: number, body: Partial<Risk>) =>
      request<Risk>(`/projects/${projectId}/risks/`, {
        method: "POST",
        body: JSON.stringify(body),
      }),

    deleteRisk: (riskId: number) =>
      request<void>(`/risks/${riskId}/`, { method: "DELETE" }),

    getStakeholders: (projectId: number) =>
      request<Stakeholder[]>(`/projects/${projectId}/stakeholders/`, {}),

    createStakeholder: (projectId: number, body: Partial<Stakeholder>) =>
      request<Stakeholder>(`/projects/${projectId}/stakeholders/`, {
        method: "POST",
        body: JSON.stringify(body),
      }),

    deleteStakeholder: (id: number) =>
      request<void>(`/stakeholders/${id}/`, { method: "DELETE" }),

    getCharter: (projectId: number) =>
      request<ProjectCharter>(`/projects/${projectId}/charter/`, {}),

    patchCharter: (projectId: number, body: Partial<ProjectCharter>) =>
      request<ProjectCharter>(`/projects/${projectId}/charter/`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),

    getRACI: (projectId: number) =>
      request<RACIEntry[]>(`/projects/${projectId}/raci/`, {}),

    createRACI: (
      projectId: number,
      body: { wbs_node_id: number; stakeholder_id: number; raci_type: string },
    ) =>
      request<RACIEntry>(`/projects/${projectId}/raci/`, {
        method: "POST",
        body: JSON.stringify(body),
      }),

    deleteRACI: (id: number) =>
      request<void>(`/raci/${id}/`, { method: "DELETE" }),

    getBaselines: (projectId: number) =>
      request<ProjectBaseline[]>(`/projects/${projectId}/baselines/`, {}),

    createBaseline: (projectId: number, name?: string) =>
      request<ProjectBaseline>(`/projects/${projectId}/baselines/`, {
        method: "POST",
        body: JSON.stringify({ name }),
      }),

    getCriticalPath: (projectId: number) =>
      request<CriticalPath>(`/projects/${projectId}/critical-path/`, {}),

    exportProject: (projectId: number) =>
      request<ProjectStatusReport>(`/projects/${projectId}/export/`, {}),

    exportProjectPdf: (projectId: number) =>
      requestBlob(`/projects/${projectId}/export/?output=pdf`),

    getWbsComments: (wbsId: number) =>
      request<WorkItemComment[]>(`/wbs/${wbsId}/comments/`, {}),

    createWbsComment: (
      wbsId: number,
      body: { body: string; kind?: "comment" | "decision" },
    ) =>
      request<WorkItemComment>(`/wbs/${wbsId}/comments/`, {
        method: "POST",
        body: JSON.stringify(body),
      }),

    getCardComments: (cardId: number) =>
      request<WorkItemComment[]>(`/cards/${cardId}/comments/`, {}),

    createCardComment: (
      cardId: number,
      body: { body: string; kind?: "comment" | "decision" },
    ) =>
      request<WorkItemComment>(`/cards/${cardId}/comments/`, {
        method: "POST",
        body: JSON.stringify(body),
      }),

    deleteComment: (commentId: number) =>
      request<void>(`/comments/${commentId}/`, { method: "DELETE" }),
  };
}
