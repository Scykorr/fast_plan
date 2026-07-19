import { request } from "./client";

export type TimeEntry = {
  id: number;
  user: number;
  user_name: string;
  wbs_node: number;
  wbs_code: string;
  wbs_title: string;
  hours: string;
  work_date: string;
  notes: string;
  created_at: string;
};

export function createTimeLogApi() {
  return {
    getEntries: (params?: { wbsNode?: number; user?: number }) => {
      const query = new URLSearchParams();
      if (params?.wbsNode != null) {
        query.set("wbs_node", String(params.wbsNode));
      }
      if (params?.user != null) {
        query.set("user", String(params.user));
      }
      const suffix = query.toString() ? `?${query.toString()}` : "";
      return request<TimeEntry[]>(`/workspace/time-entries/${suffix}`, {});
    },

    createEntry: (body: {
      wbs_node: number;
      hours: string;
      work_date: string;
      notes?: string;
    }) =>
      request<TimeEntry>("/workspace/time-entries/", {
        method: "POST",
        body: JSON.stringify(body),
      }),

    updateEntry: (
      id: number,
      body: Partial<{ hours: string; work_date: string; notes: string }>,
    ) =>
      request<TimeEntry>(`/workspace/time-entries/${id}/`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),

    deleteEntry: (id: number) =>
      request<void>(`/workspace/time-entries/${id}/`, { method: "DELETE" }),
  };
}
