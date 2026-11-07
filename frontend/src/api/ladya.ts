import { request, requestForm } from "./client";

export type LadyaSettings = {
  ladya_hub_enabled: boolean;
  package_max_bytes: number;
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
  source: "web_form" | "manual" | "internal_chat" | "telegram";
  package: number | null;
  created_by: number | null;
  created_at: string;
  updated_at: string;
};

export function createLadyaApi() {
  return {
    getSettings: () => request<LadyaSettings>("/ladya/settings/"),
    patchSettings: (data: { ladya_hub_enabled?: boolean }) =>
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
    ensureLaboratoryChat: (id: number) =>
      request<{
        laboratory: Laboratory;
        chat_room_id: number;
        open_path: string;
      }>(`/ladya/laboratories/${id}/ensure-chat/`, {
        method: "POST",
        body: JSON.stringify({}),
      }),
    listLaboratoryAgents: (labId: number) =>
      request<
        Array<{
          id: number;
          display_name: string;
          role: string;
          ladya_role: string;
          user_email: string;
          is_active: boolean;
          is_service_account: boolean;
        }>
      >(`/ladya/laboratories/${labId}/agents/`),

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
    notifyPackageChat: (id: number, text?: string) =>
      request<{ message_id: number; room_id: number; body: string }>(
        `/ladya/packages/${id}/notify-chat/`,
        {
          method: "POST",
          body: JSON.stringify(text ? { text } : {}),
        },
      ),
    chatCapabilities: (roomId: number) =>
      request<{
        ladya_enabled: boolean;
        can_create_intake: boolean;
        lab_ids: number[];
      }>(`/ladya/chat-rooms/${roomId}/capabilities/`),
    intakeFromChatMessage: (messageId: number) =>
      request<IntakeRequest>("/ladya/intake/from-chat-message/", {
        method: "POST",
        body: JSON.stringify({ message_id: messageId }),
      }),
    listLadyaAgents: (laboratory?: number) => {
      const q =
        laboratory != null ? `?laboratory=${laboratory}` : "";
      return request<
        Array<{
          id: number;
          display_name: string;
          role: string;
          ladya_role: string;
          user_email: string;
          is_active: boolean;
          is_service_account: boolean;
        }>
      >(`/ladya/agents/${q}`);
    },
    connectAgent: (data: {
      ladya_role: string;
      display_name?: string;
      laboratory?: number | null;
      ops_role?: string;
      frontend_base_url?: string;
    }) =>
      request<{
        id: number;
        display_name: string;
        role: string;
        ladya_role: string;
        user_email: string;
        api_token_raw: string | null;
        service_user_email: string | null;
        workspace_id: number;
        connect_instruction: string;
        laboratory_id: number | null;
      }>("/ladya/agents/", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    reissueAgent: (id: number, frontend_base_url?: string) =>
      request<{
        id: number;
        api_token_raw: string;
        connect_instruction: string;
        workspace_id: number;
      }>(`/ladya/agents/${id}/reissue/`, {
        method: "POST",
        body: JSON.stringify(
          frontend_base_url ? { frontend_base_url } : {},
        ),
      }),
    revokeAgent: (id: number) =>
      request<{ id: number; is_active: boolean }>(
        `/ladya/agents/${id}/revoke/`,
        { method: "POST", body: JSON.stringify({}) },
      ),
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
