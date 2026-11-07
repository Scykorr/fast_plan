import { request, requestForm } from "./client";

export type LadyaSettings = {
  ladya_hub_enabled: boolean;
  package_max_bytes: number;
  telegram_webhook_secret_set: boolean;
  telegram_webhook_path: string;
  updated_at: string;
};

export type LadyaRole =
  | ""
  | "lad"
  | "cartographer"
  | "quest"
  | "curator";

export type LadyaStatusEvent = {
  id: number;
  from_status: string;
  to_status: string;
  from_laboratory: number | null;
  to_laboratory: number | null;
  reason: string;
  changed_by: number | null;
  created_at: string;
  package_id?: number;
  package_code?: string;
  package_title?: string;
};

export type LaboratoryKind =
  | "central_lad"
  | "lab0"
  | "private_lab"
  | "external_intake";

export type Laboratory = {
  id: number;
  slug: string;
  title: string;
  kind: LaboratoryKind;
  is_active: boolean;
  chat_room: number | null;
  created_at: string;
  updated_at: string;
};

export type PackageStatus =
  | "draft"
  | "submitted"
  | "accepted"
  | "in_progress"
  | "returned"
  | "closed"
  | "rejected";

export type PackageFile = {
  id: number;
  original_name: string;
  size: number;
  sha256: string;
  content_type: string;
  uploaded_by: number | null;
  created_at: string;
  file: string;
};

export type PackageStatusEvent = {
  id: number;
  from_status: string;
  to_status: string;
  from_laboratory: number | null;
  to_laboratory: number | null;
  reason: string;
  changed_by: number | null;
  created_at: string;
};

export type LadyaPackage = {
  id: number;
  public_number: number;
  display_code: string;
  title: string;
  summary: string;
  from_laboratory: number | null;
  to_laboratory: number | null;
  status: PackageStatus;
  created_by: number;
  linked_delivery_task: number | null;
  preferred_role: LadyaRole | string;
  manifest_sha256: string;
  notes_limitations: string;
  created_at: string;
  updated_at: string;
  files: PackageFile[];
  status_events: PackageStatusEvent[];
};

export type IntakeStatus = "new" | "triaged" | "converted" | "closed";

export type IntakeRequest = {
  id: number;
  body: string;
  contact: string;
  status: IntakeStatus;
  source: "web_form" | "manual" | "telegram";
  package: number | null;
  created_by: number | null;
  created_at: string;
  updated_at: string;
};

export function createLadyaApi() {
  return {
    getSettings: () => request<LadyaSettings>("/ladya/settings/"),
    patchSettings: (data: {
      ladya_hub_enabled?: boolean;
      rotate_telegram_webhook_secret?: boolean;
    }) =>
      request<LadyaSettings>("/ladya/settings/", {
        method: "PATCH",
        body: JSON.stringify(data),
      }),

    listLaboratories: () => request<Laboratory[]>("/ladya/laboratories/"),
    createLaboratory: (data: {
      slug: string;
      title: string;
      kind: LaboratoryKind;
      is_active?: boolean;
    }) =>
      request<Laboratory>("/ladya/laboratories/", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    patchLaboratory: (
      id: number,
      data: Partial<{
        slug: string;
        title: string;
        kind: LaboratoryKind;
        is_active: boolean;
        chat_room: number | null;
      }>,
    ) =>
      request<Laboratory>(`/ladya/laboratories/${id}/`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    deleteLaboratory: (id: number) =>
      request<void>(`/ladya/laboratories/${id}/`, { method: "DELETE" }),

    listPackages: (params?: {
      status?: string;
      from_lab?: number;
      to_lab?: number;
      q?: string;
    }) => {
      const q = new URLSearchParams();
      if (params?.status) q.set("status", params.status);
      if (params?.from_lab != null) q.set("from_lab", String(params.from_lab));
      if (params?.to_lab != null) q.set("to_lab", String(params.to_lab));
      if (params?.q) q.set("q", params.q);
      const suffix = q.toString() ? `?${q}` : "";
      return request<LadyaPackage[]>(`/ladya/packages/${suffix}`);
    },
    getPackage: (id: number) => request<LadyaPackage>(`/ladya/packages/${id}/`),
    createPackage: (data: {
      title: string;
      summary?: string;
      from_laboratory?: number | null;
      to_laboratory?: number | null;
      linked_delivery_task?: number | null;
      preferred_role?: string;
      notes_limitations?: string;
    }) =>
      request<LadyaPackage>("/ladya/packages/", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    patchPackage: (
      id: number,
      data: Partial<{
        title: string;
        summary: string;
        from_laboratory: number | null;
        to_laboratory: number | null;
        linked_delivery_task: number | null;
        preferred_role: string;
        notes_limitations: string;
      }>,
    ) =>
      request<LadyaPackage>(`/ladya/packages/${id}/`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    transitionPackage: (
      id: number,
      data: {
        status: PackageStatus;
        reason?: string;
        to_laboratory?: number | null;
      },
    ) =>
      request<LadyaPackage>(`/ladya/packages/${id}/transition/`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    uploadPackageFile: (id: number, file: File) => {
      const form = new FormData();
      form.append("file", file);
      return requestForm<PackageFile>(`/ladya/packages/${id}/files/`, form);
    },
    transferPackage: (
      id: number,
      data: { to_laboratory: number; reason?: string },
    ) =>
      request<LadyaPackage>(`/ladya/packages/${id}/transfer/`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    createDeliveryTask: (id: number) =>
      request<{
        package: LadyaPackage;
        delivery_task: {
          id: number;
          title: string;
          status: string;
          assignee: number | null;
        };
      }>(`/ladya/packages/${id}/create-delivery-task/`, {
        method: "POST",
        body: JSON.stringify({}),
      }),
    buildManifest: (id: number) =>
      request<{ manifest: Record<string, unknown>; manifest_sha256: string }>(
        `/ladya/packages/${id}/manifest/`,
        { method: "POST", body: JSON.stringify({}) },
      ),
    listLabPackages: (
      labId: number,
      params?: { direction?: string; status?: string },
    ) => {
      const q = new URLSearchParams();
      if (params?.direction) q.set("direction", params.direction);
      if (params?.status) q.set("status", params.status);
      const suffix = q.toString() ? `?${q}` : "";
      return request<{ laboratory: Laboratory; packages: LadyaPackage[] }>(
        `/ladya/laboratories/${labId}/packages/${suffix}`,
      );
    },
    listEvents: (limit = 30) =>
      request<LadyaStatusEvent[]>(`/ladya/events/?limit=${limit}`),

    listIntake: (status?: string) =>
      request<IntakeRequest[]>(
        status
          ? `/ladya/intake/?status=${encodeURIComponent(status)}`
          : "/ladya/intake/",
      ),
    createIntake: (data: {
      body: string;
      contact?: string;
      source?: "web_form" | "manual";
    }) =>
      request<IntakeRequest>("/ladya/intake/", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    triageIntake: (id: number, status: "triaged" | "closed") =>
      request<IntakeRequest>(`/ladya/intake/${id}/triage/`, {
        method: "POST",
        body: JSON.stringify({ status }),
      }),
    convertIntake: (
      id: number,
      data: {
        title?: string;
        summary?: string;
        from_laboratory?: number | null;
        to_laboratory?: number | null;
      },
    ) =>
      request<{ intake: IntakeRequest; package: LadyaPackage }>(
        `/ladya/intake/${id}/convert/`,
        {
          method: "POST",
          body: JSON.stringify(data),
        },
      ),
  };
}
