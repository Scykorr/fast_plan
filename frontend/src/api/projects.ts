import { request, requestBlob, requestForm } from "./client";

export type Project = {
  id: number;
  name: string;
  description: string;
  status: string;
  methodology?: "predictive" | "scrum" | "hybrid" | string;
  schedule_locked?: boolean;
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
  ai_prompts?: Record<string, string>;
  client_organization_id?: number | null;
  client_organization_name?: string | null;
};

export type ProjectTemplate = {
  id: number;
  name: string;
  description: string;
  created_by: number | null;
  created_at: string;
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

export type ProjectLessonsLearned = {
  what_went_well: string;
  what_went_wrong: string;
  recommendations: string;
  knowledge_to_reuse: string;
  updated_at: string;
};

export type WBSQualityCheckItem = {
  id: number;
  wbs_node: number;
  title: string;
  result: "open" | "pass" | "fail" | string;
  evidence_url: string;
  position: number;
  checked_by: number | null;
  checked_by_name: string | null;
  checked_at: string | null;
  created_at: string;
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

export type ProjectIssue = {
  id: number;
  title: string;
  description: string;
  issue_type: string;
  priority: string;
  status: string;
  owner_id: number | null;
  owner_name: string | null;
  due_date: string | null;
  action: string;
  related_risk_id: number | null;
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
  stakeholder_id: number | null;
  stakeholder_name: string | null;
  obs_role_id: number | null;
  obs_role_name: string | null;
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

export type ProjectChangeRequest = {
  id: number;
  project: number;
  title: string;
  description: string;
  change_type: "scope" | "schedule" | "cost" | "other" | string;
  status: "draft" | "submitted" | "approved" | "rejected" | string;
  impact_notes: string;
  decision_note: string;
  baseline: number | null;
  baseline_name: string | null;
  requested_by: number | null;
  requested_by_email: string | null;
  decided_by: number | null;
  decided_by_email: string | null;
  created_at: string;
  updated_at: string;
  decided_at: string | null;
};

export type EvmLite = {
  budget: number;
  earned_value: number;
  planned_value: number;
  actual_cost: number;
  cpi: number | null;
  spi: number | null;
  percent_complete: number;
  earned_schedule_date?: string | null;
  schedule_variance_time?: number | null;
  spi_t?: number | null;
  planned_duration_days?: number | null;
  earned_duration_days?: number | null;
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

export type CapacityHint = {
  week_start: string;
  week_end: string;
  capacity_hours: number;
  allocated_hours: number;
  utilization: number | null;
  overloaded: boolean;
  hint: string | null;
};

export type LevelingProposal = {
  activity_id: number;
  wbs_id: number;
  code: string;
  name: string;
  assignee_id: number;
  current: { start_date: string; end_date: string; duration_days: number };
  proposed: { start_date: string; end_date: string; duration_days: number };
  shift_days: number;
  reason: string;
};

export type LevelingProposeResult = {
  week_start: string;
  week_end: string;
  overloaded_assignees: Array<{
    assignee_id: number;
    utilization_before: number | null;
    capacity_hours: number;
    allocated_hours: number;
  }>;
  proposals: LevelingProposal[];
  unresolved: Array<{ assignee_id: number; detail: string }>;
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
  org_unit_id?: number | null;
  org_unit_name?: string | null;
  obs_role_id?: number | null;
  obs_role_name?: string | null;
  phase_key?: string | null;
  phase_order?: number | null;
  gate_status?: string | null;
  custom_values: CustomValue[];
  schedule: ScheduleActivity | null;
  capacity_hint?: CapacityHint | null;
  card_id: number | null;
  quality?: {
    total: number;
    passed: number;
    failed: number;
    open: number;
  };
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
  assignee_id?: number | null;
  assignee_name?: string | null;
  capacity_hint?: CapacityHint | null;
};

export type ActivityDependency = {
  id: number;
  predecessor_id: number;
  successor_id: number;
  dependency_type: string;
  lag_days: number;
};

export type ProjectSchedule = {
  week_start?: string | null;
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
  share?: {
    label: string;
    project_name: string;
    workspace_name: string;
    allow_chat?: boolean;
    chat_can_post?: boolean;
  };
};

export type ImportResult = {
  created: number;
  updated?: number;
  errors: string[];
  headers?: string[];
};

export type PertNode = {
  id: number;
  wbs_id: number;
  code: string;
  name: string;
  optimistic_days: number;
  most_likely_days: number;
  pessimistic_days: number;
  expected_days: number;
  early_start: number | null;
  early_finish: number | null;
  late_start: number | null;
  late_finish: number | null;
  slack: number | null;
  is_critical: boolean;
};

export type PertEdge = {
  id: number;
  from: number;
  to: number;
  type: string;
  lag_days: number;
};

export type PertFinish = {
  mean_days: number;
  sigma_days: number;
  p10_days: number;
  p50_days: number;
  p90_days: number;
  method: string;
  trials?: number;
  start_date?: string;
  p10_date?: string;
  p50_date?: string;
  p90_date?: string;
};

export type PertNetwork = {
  nodes: PertNode[];
  edges: PertEdge[];
  project_duration: number;
  critical_path_ids: number[];
  finish?: PertFinish;
};

export type WorkspaceScheduleActivity = {
  id: number;
  name: string;
  code: string;
  project_id: number;
  project_name: string;
  start_date: string | null;
  end_date: string | null;
  is_milestone: boolean;
};

export type CrossProjectDependency = {
  id: number;
  predecessor_id: number;
  successor_id: number;
  predecessor_project_id?: number;
  successor_project_id?: number;
  predecessor_title?: string;
  successor_title?: string;
  dependency_type: string;
  lag_days: number;
  note: string;
  created_at?: string;
  created?: boolean;
};

export type ShareLink = {
  id: number;
  token: string;
  label: string;
  created_at: string;
  expires_at: string | null;
  last_accessed_at: string | null;
  is_active: boolean;
  allow_chat?: boolean;
  chat_can_post?: boolean;
  url_path?: string;
};

export type ProjectMember = {
  id: number;
  user_id: number;
  email: string;
  username: string;
  role: "manager" | "contributor" | "viewer";
  created_at: string;
};

export type WorkItemComment = {
  id: number;
  kind: "comment" | "decision";
  body: string;
  author: number;
  author_name: string;
  wbs_node_id: number | null;
  card_id: number | null;
  process_work_node_id?: number | null;
  created_at: string;
  updated_at: string;
};

export type ProjectPatchBody = {
  name?: string;
  description?: string;
  status?: string;
  methodology?: "predictive" | "scrum" | "hybrid" | string;
  start_date?: string | null;
  end_date?: string | null;
  budget?: number;
  manager?: number | null;
  tracker_id?: number | null;
  workflow_status_id?: number | null;
  custom_values?: Record<string, string>;
  ai_prompts?: Record<string, string>;
  client_organization_id?: number | null;
};

export type AiDraftWbsNode = {
  code: string;
  title: string;
  node_type?: string;
  parent_code?: string;
  duration_days?: number;
  start_date?: string;
  end_date?: string;
};

export type AiDraftWbsDependency = {
  predecessor_code: string;
  successor_code: string;
  dependency_type?: string;
  lag_days?: number;
};

export type AiDraftTarget = "risks" | "charter" | "wbs";

export type WaterfallPhase = {
  id: number;
  code: string;
  title: string;
  phase_key: string | null;
  phase_order: number | null;
  gate_status: string | null;
  progress: number;
  start_date: string | null;
  end_date: string | null;
};

export type PhaseGateRecord = {
  id: number;
  project: number;
  wbs_phase_node: number;
  phase_title: string;
  phase_key: string | null;
  checklist: Array<{ id: string; label: string; done?: boolean }>;
  decision: "pass" | "fail" | string;
  comment: string;
  decided_by: number | null;
  decided_by_email: string | null;
  decided_at: string;
  baseline: number | null;
  baseline_name: string | null;
  process_instance: number | null;
};

export type WaterfallOverview = {
  methodology: string;
  schedule_locked: boolean;
  default_checklist: Array<{ id: string; label: string; done?: boolean }>;
  phases: WaterfallPhase[];
  gates: PhaseGateRecord[];
};

export function createProjectsApi() {
  return {
    getProjects: () => request<Project[]>("/projects/", {}),

    createProject: (body: {
      name: string;
      description?: string;
      status?: string;
      methodology?: string;
      seed_waterfall?: boolean;
      start_date?: string;
      end_date?: string;
      budget?: number;
      template_id?: number;
    }) =>
      request<Project>("/projects/", {
        method: "POST",
        body: JSON.stringify(body),
      }),

    getProjectTemplates: () =>
      request<ProjectTemplate[]>("/project-templates/", {}),

    createProjectTemplate: (body: {
      name: string;
      description?: string;
      source_project_id: number;
    }) =>
      request<ProjectTemplate>("/project-templates/", {
        method: "POST",
        body: JSON.stringify(body),
      }),

    deleteProjectTemplate: (templateId: number) =>
      request<void>(`/project-templates/${templateId}/`, { method: "DELETE" }),

    getProject: (id: number) =>
      request<Project>(`/projects/${id}/`, {}),

    patchProject: (id: number, body: ProjectPatchBody) =>
      request<Project>(`/projects/${id}/`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),

    deleteProject: (id: number) =>
      request<void>(`/projects/${id}/`, { method: "DELETE" }),

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
        org_unit_id?: number | null;
        obs_role_id?: number | null;
        custom_values?: Record<string, string>;
      },
    ) =>
      request<WBSNode[]>(`/wbs/${wbsId}/`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),

    deleteWBSNode: (wbsId: number) =>
      request<void>(`/wbs/${wbsId}/`, { method: "DELETE" }),

    getQualityChecks: (wbsId: number) =>
      request<WBSQualityCheckItem[]>(`/wbs/${wbsId}/quality-checks/`, {}),

    createQualityCheck: (
      wbsId: number,
      body: { title: string; evidence_url?: string; result?: string },
    ) =>
      request<WBSQualityCheckItem>(`/wbs/${wbsId}/quality-checks/`, {
        method: "POST",
        body: JSON.stringify(body),
      }),

    updateQualityCheck: (
      itemId: number,
      body: { title?: string; evidence_url?: string; result?: string; position?: number },
    ) =>
      request<WBSQualityCheckItem>(`/quality-checks/${itemId}/`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),

    deleteQualityCheck: (itemId: number) =>
      request<void>(`/quality-checks/${itemId}/`, { method: "DELETE" }),

    getSchedule: (projectId: number) =>
      request<ProjectSchedule>(`/projects/${projectId}/schedule/`, {}),

    proposeLeveling: (
      projectId: number,
      body: { week_start?: string; max_shift_days?: number; assignee_id?: number } = {},
    ) =>
      request<LevelingProposeResult>(
        `/projects/${projectId}/schedule/leveling/propose/`,
        { method: "POST", body: JSON.stringify(body) },
      ),

    applyLeveling: (projectId: number, proposals: LevelingProposal[]) =>
      request<{
        applied: Array<{ activity_id: number; before: LevelingProposal["current"]; after: LevelingProposal["proposed"] }>;
        undo_token: string | null;
        batch: { created_at: string; project_id?: number; items: Array<LevelingProposal["current"] & { activity_id: number }> };
      }>(`/projects/${projectId}/schedule/leveling/apply/`, {
        method: "POST",
        body: JSON.stringify({ proposals }),
      }),

    undoLeveling: (
      projectId: number,
      items: Array<{ activity_id: number; start_date: string | null; end_date: string | null; duration_days?: number }>,
    ) =>
      request<{ restored: Array<{ activity_id: number }>; count: number }>(
        `/projects/${projectId}/schedule/leveling/undo/`,
        { method: "POST", body: JSON.stringify({ items }) },
      ),

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

    updateRisk: (
      riskId: number,
      body: Partial<{
        title: string;
        description: string;
        probability: number;
        impact: number;
        status: string;
        mitigation: string;
      }>,
    ) =>
      request<Risk>(`/risks/${riskId}/`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),

    deleteRisk: (riskId: number) =>
      request<void>(`/risks/${riskId}/`, { method: "DELETE" }),

    getIssues: (projectId: number) =>
      request<ProjectIssue[]>(`/projects/${projectId}/issues/`, {}),

    createIssue: (
      projectId: number,
      body: Partial<{
        title: string;
        description: string;
        issue_type: string;
        priority: string;
        status: string;
        owner_id: number | null;
        due_date: string | null;
        action: string;
        related_risk_id: number | null;
      }>,
    ) =>
      request<ProjectIssue>(`/projects/${projectId}/issues/`, {
        method: "POST",
        body: JSON.stringify(body),
      }),

    updateIssue: (
      issueId: number,
      body: Partial<{
        title: string;
        description: string;
        issue_type: string;
        priority: string;
        status: string;
        owner_id: number | null;
        due_date: string | null;
        action: string;
        related_risk_id: number | null;
      }>,
    ) =>
      request<ProjectIssue>(`/issues/${issueId}/`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),

    deleteIssue: (issueId: number) =>
      request<void>(`/issues/${issueId}/`, { method: "DELETE" }),

    getStakeholders: (projectId: number) =>
      request<Stakeholder[]>(`/projects/${projectId}/stakeholders/`, {}),

    createStakeholder: (projectId: number, body: Partial<Stakeholder>) =>
      request<Stakeholder>(`/projects/${projectId}/stakeholders/`, {
        method: "POST",
        body: JSON.stringify(body),
      }),

    updateStakeholder: (
      id: number,
      body: Partial<{
        name: string;
        role: string;
        interest: number;
        influence: number;
        contact_email: string;
        notes: string;
      }>,
    ) =>
      request<Stakeholder>(`/stakeholders/${id}/`, {
        method: "PATCH",
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

    getLessonsLearned: (projectId: number) =>
      request<ProjectLessonsLearned>(
        `/projects/${projectId}/lessons-learned/`,
        {},
      ),

    patchLessonsLearned: (
      projectId: number,
      body: Partial<ProjectLessonsLearned>,
    ) =>
      request<ProjectLessonsLearned>(
        `/projects/${projectId}/lessons-learned/`,
        {
          method: "PATCH",
          body: JSON.stringify(body),
        },
      ),

    exportLessonsLearned: (projectId: number, output: "md" | "pdf" = "md") =>
      requestBlob(
        `/projects/${projectId}/lessons-learned/export/?output=${output}`,
      ),

    getRACI: (projectId: number) =>
      request<RACIEntry[]>(`/projects/${projectId}/raci/`, {}),

    createRACI: (
      projectId: number,
      body: {
        wbs_node_id: number;
        stakeholder_id?: number | null;
        obs_role_id?: number | null;
        raci_type: string;
      },
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

    updateBaseline: (baselineId: number, name: string) =>
      request<ProjectBaseline>(`/baselines/${baselineId}/`, {
        method: "PATCH",
        body: JSON.stringify({ name }),
      }),

    deleteBaseline: (baselineId: number) =>
      request<void>(`/baselines/${baselineId}/`, { method: "DELETE" }),

    getChangeRequests: (projectId: number) =>
      request<ProjectChangeRequest[]>(
        `/projects/${projectId}/change-requests/`,
        {},
      ),
    createChangeRequest: (
      projectId: number,
      body: {
        title: string;
        description?: string;
        change_type?: string;
        impact_notes?: string;
        status?: string;
      },
    ) =>
      request<ProjectChangeRequest>(`/projects/${projectId}/change-requests/`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    decideChangeRequest: (
      crId: number,
      body: { action: "approve" | "reject"; note?: string; create_baseline?: boolean },
    ) =>
      request<ProjectChangeRequest>(`/change-requests/${crId}/decide/`, {
        method: "POST",
        body: JSON.stringify(body),
      }),

    getWaterfall: (projectId: number) =>
      request<WaterfallOverview>(`/projects/${projectId}/waterfall/`, {}),

    seedWaterfall: (
      projectId: number,
      body: { replace?: boolean; set_methodology?: boolean } = {},
    ) =>
      request<{
        project: {
          id: number;
          methodology: string;
          schedule_locked: boolean;
        };
        wbs: WBSNode[];
      }>(`/projects/${projectId}/waterfall/`, {
        method: "POST",
        body: JSON.stringify(body),
      }),

    decidePhaseGate: (
      projectId: number,
      body: {
        wbs_phase_node_id: number;
        decision: "pass" | "fail";
        comment?: string;
        checklist?: Array<{ id: string; label: string; done?: boolean }>;
        create_baseline?: boolean;
        lock_schedule?: boolean;
      },
    ) =>
      request<{
        gate: PhaseGateRecord;
        schedule_locked: boolean;
        phase: {
          id: number;
          gate_status: string | null;
          phase_key: string | null;
        };
      }>(`/projects/${projectId}/waterfall/gates/`, {
        method: "POST",
        body: JSON.stringify(body),
      }),

    addWaterfallPhase: (
      projectId: number,
      body: {
        title: string;
        duration_days?: number;
        after_phase_id?: number | null;
        phase_key?: string | null;
      },
    ) =>
      request<WaterfallPhase>(`/projects/${projectId}/waterfall/phases/`, {
        method: "POST",
        body: JSON.stringify(body),
      }),

    renameWaterfallPhase: (
      projectId: number,
      phaseId: number,
      title: string,
    ) =>
      request<WaterfallPhase>(
        `/projects/${projectId}/waterfall/phases/${phaseId}/`,
        {
          method: "PATCH",
          body: JSON.stringify({ title }),
        },
      ),

    deleteWaterfallPhase: (projectId: number, phaseId: number) =>
      request<void>(`/projects/${projectId}/waterfall/phases/${phaseId}/`, {
        method: "DELETE",
      }),

    getCriticalPath: (projectId: number) =>
      request<CriticalPath>(`/projects/${projectId}/critical-path/`, {}),

    exportProject: (projectId: number) =>
      request<ProjectStatusReport>(`/projects/${projectId}/export/`, {}),

    exportProjectPdf: (projectId: number) =>
      requestBlob(`/projects/${projectId}/export/?output=pdf`),

    exportWbs: (projectId: number, format: "csv" | "xlsx") =>
      requestBlob(`/projects/${projectId}/export/?output=${format}`),

    downloadProjectMilestonesIcs: (projectId: number) =>
      requestBlob(`/projects/${projectId}/milestones.ics`),

    downloadWorkspaceCalendarIcs: () => requestBlob("/workspace/calendar.ics"),

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

    importWbs: (projectId: number, file: File, format: "wbs" | "jira" = "wbs") => {
      const form = new FormData();
      form.append("file", file);
      form.append("format", format);
      return requestForm<ImportResult>(`/projects/${projectId}/import/`, form);
    },

    draftProjectContent: (
      projectId: number,
      body: {
        target: AiDraftTarget;
        prompt?: string;
        refinement?: string;
        current_draft?: {
          nodes: AiDraftWbsNode[];
          dependencies?: AiDraftWbsDependency[];
        };
      },
    ) =>
      request<
        | {
            target: "risks";
            source: string;
            saved_prompt?: string;
            risks: Array<{
              title: string;
              description?: string;
              probability: number;
              impact: number;
              mitigation?: string;
              status?: string;
            }>;
          }
        | {
            target: "charter";
            source: string;
            saved_prompt?: string;
            charter: ProjectCharter;
          }
        | {
            target: "wbs";
            source: string;
            saved_prompt?: string;
            refinement?: string;
            nodes: AiDraftWbsNode[];
            dependencies: AiDraftWbsDependency[];
          }
      >(`/projects/${projectId}/ai-draft/`, {
        method: "POST",
        body: JSON.stringify(body),
      }),

    getAiPrompts: (projectId: number) =>
      request<{ ai_prompts: Record<string, string> }>(
        `/projects/${projectId}/ai-draft/`,
        {},
      ),

    applyAiDraft: (
      projectId: number,
      body: {
        target: "wbs";
        nodes: AiDraftWbsNode[];
        dependencies?: AiDraftWbsDependency[];
      },
    ) =>
      request<{
        created: number;
        updated: number;
        dependencies_created: number;
        errors: string[];
      }>(`/projects/${projectId}/ai-draft/apply/`, {
        method: "POST",
        body: JSON.stringify(body),
      }),

    getPert: (
      projectId: number,
      opts?: { method?: "normal" | "monte_carlo"; trials?: number },
    ) => {
      const q = new URLSearchParams();
      if (opts?.method) q.set("method", opts.method);
      if (opts?.trials) q.set("trials", String(opts.trials));
      const suffix = q.toString() ? `?${q}` : "";
      return request<PertNetwork>(`/projects/${projectId}/pert/${suffix}`, {});
    },

    getShareLinks: (projectId: number) =>
      request<ShareLink[]>(`/projects/${projectId}/share-links/`, {}),

    createShareLink: (
      projectId: number,
      body: {
        label?: string;
        expires_at?: string;
        allow_chat?: boolean;
        chat_can_post?: boolean;
      },
    ) =>
      request<ShareLink>(`/projects/${projectId}/share-links/`, {
        method: "POST",
        body: JSON.stringify(body),
      }),

    revokeShareLink: (projectId: number, linkId: number) =>
      request<void>(`/projects/${projectId}/share-links/${linkId}/`, {
        method: "DELETE",
      }),

    getProjectMembers: (projectId: number) =>
      request<ProjectMember[]>(`/projects/${projectId}/members/`, {}),

    addProjectMember: (
      projectId: number,
      body: { user_id: number; role: ProjectMember["role"] },
    ) =>
      request<ProjectMember>(`/projects/${projectId}/members/`, {
        method: "POST",
        body: JSON.stringify(body),
      }),

    removeProjectMember: (projectId: number, memberId: number) =>
      request<void>(`/projects/${projectId}/members/${memberId}/`, {
        method: "DELETE",
      }),

    listCrossDependencies: () =>
      request<CrossProjectDependency[]>("/workspace/cross-dependencies/", {}),

    createCrossDependency: (body: {
      predecessor_id: number;
      successor_id: number;
      dependency_type?: string;
      lag_days?: number;
      note?: string;
    }) =>
      request<CrossProjectDependency>("/workspace/cross-dependencies/", {
        method: "POST",
        body: JSON.stringify(body),
      }),

    deleteCrossDependency: (depId: number) =>
      request<void>(`/workspace/cross-dependencies/${depId}/`, {
        method: "DELETE",
      }),

    listWorkspaceScheduleActivities: (params: { q?: string; project_id?: number } = {}) => {
      const qs = new URLSearchParams();
      if (params.q) qs.set("q", params.q);
      if (params.project_id != null) qs.set("project_id", String(params.project_id));
      const suffix = qs.toString() ? `?${qs}` : "";
      return request<WorkspaceScheduleActivity[]>(
        `/workspace/schedule-activities/${suffix}`,
        {},
      );
    },
  };
}

const API_BASE = "/api";

export async function fetchPublicStatusReport(
  token: string,
): Promise<ProjectStatusReport> {
  const response = await fetch(`${API_BASE}/share/${token}/`);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : "Ссылка не найдена или истекла",
    );
  }
  return data as ProjectStatusReport;
}
