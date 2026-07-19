import { request } from "./client";

export type AuditLogEntry = {
  id: number;
  action: string;
  entity_type: string;
  entity_id: number;
  summary: string;
  changes: Record<string, unknown> | null;
  actor: number | null;
  actor_name: string | null;
  created_at: string;
};

export type AuditLogPage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: AuditLogEntry[];
};

export function createAuditApi() {
  return {
    getAuditLog: (page = 1) =>
      request<AuditLogPage>(`/workspace/audit/?page=${page}`, {}),
  };
}
