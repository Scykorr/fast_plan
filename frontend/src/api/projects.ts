import { request } from "./client";

export type Project = {
  id: number;
  name: string;
  description: string;
  status: string;
  start_date: string | null;
  end_date: string | null;
  manager: number | null;
  created_at: string;
  updated_at: string;
  wbs_count: number;
  progress: number;
  board_id: number | null;
};

export type ProjectDashboard = {
  project_id: number;
  name: string;
  status: string;
  progress: number;
  wbs_count: number;
  upcoming_milestones: ScheduleActivity[];
};

export type WBSNode = {
  id: number;
  code: string;
  title: string;
  description: string;
  node_type: string;
  position: number;
  parent_id: number | null;
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

export function createProjectsApi(token: string) {
  return {
    getProjects: () => request<Project[]>("/projects/", {}, token),

    createProject: (body: {
      name: string;
      description?: string;
      status?: string;
      start_date?: string;
      end_date?: string;
    }) =>
      request<Project>("/projects/", {
        method: "POST",
        body: JSON.stringify(body),
      }, token),

    getProject: (id: number) =>
      request<Project>(`/projects/${id}/`, {}, token),

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
  };
}
