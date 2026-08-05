import { request } from "./client";

export type ScrumSprint = {
  id: number;
  name: string;
  goal: string;
  starts_on: string | null;
  ends_on: string | null;
  status: "planned" | "active" | "completed" | string;
  pbi_count: number;
  committed_points: number;
  remaining_points: number;
  created_at: string;
  updated_at: string;
};

export type ProductBacklogItem = {
  id: number;
  title: string;
  description: string;
  story_points: number | null;
  priority: number;
  rank: number;
  status: "todo" | "in_progress" | "done" | string;
  sprint_id: number | null;
  assignee_id: number | null;
  assignee_name: string | null;
  created_at: string;
  updated_at: string;
};

export type ScrumBurndown = {
  sprint_id: number;
  committed_points: number;
  remaining_points: number;
  burndown: Array<{
    date: string;
    remaining: number | null;
    ideal: number;
  }>;
};

export function createScrumApi() {
  return {
    listBacklog: (projectId: number, scope?: "product" | "committed") => {
      const q = scope ? `?scope=${scope}` : "";
      return request<ProductBacklogItem[]>(
        `/projects/${projectId}/scrum/backlog/${q}`,
        {},
      );
    },
    createPbi: (
      projectId: number,
      body: Partial<{
        title: string;
        description: string;
        story_points: number | null;
        priority: number;
        rank: number;
        status: string;
        assignee_id: number | null;
        sprint_id: number | null;
      }>,
    ) =>
      request<ProductBacklogItem>(`/projects/${projectId}/scrum/backlog/`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    updatePbi: (
      pbiId: number,
      body: Partial<{
        title: string;
        description: string;
        story_points: number | null;
        priority: number;
        rank: number;
        status: string;
        assignee_id: number | null;
        sprint_id: number | null;
      }>,
    ) =>
      request<ProductBacklogItem>(`/scrum/pbis/${pbiId}/`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    deletePbi: (pbiId: number) =>
      request<void>(`/scrum/pbis/${pbiId}/`, { method: "DELETE" }),
    listSprints: (projectId: number) =>
      request<ScrumSprint[]>(`/projects/${projectId}/scrum/sprints/`, {}),
    createSprint: (
      projectId: number,
      body: Partial<{
        name: string;
        goal: string;
        starts_on: string | null;
        ends_on: string | null;
        status: string;
      }>,
    ) =>
      request<ScrumSprint>(`/projects/${projectId}/scrum/sprints/`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    activateSprint: (sprintId: number) =>
      request<ScrumSprint>(`/scrum/sprints/${sprintId}/activate/`, {
        method: "POST",
        body: JSON.stringify({}),
      }),
    completeSprint: (sprintId: number) =>
      request<ScrumSprint>(`/scrum/sprints/${sprintId}/complete/`, {
        method: "POST",
        body: JSON.stringify({}),
      }),
    commitToSprint: (sprintId: number, pbiIds: number[]) =>
      request<{ committed: number; sprint_id: number }>(
        `/scrum/sprints/${sprintId}/commit/`,
        {
          method: "POST",
          body: JSON.stringify({ pbi_ids: pbiIds }),
        },
      ),
    sprintBacklog: (sprintId: number) =>
      request<ProductBacklogItem[]>(`/scrum/sprints/${sprintId}/backlog/`, {}),
    burndown: (sprintId: number) =>
      request<ScrumBurndown>(`/scrum/sprints/${sprintId}/burndown/`, {}),
  };
}
