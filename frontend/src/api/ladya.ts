import { request, requestForm } from "./client";

export type LadyaSettings = {
  ladya_hub_enabled: boolean;
  updated_at: string;
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
  source: "web_form" | "manual";
  package: number | null;
  created_by: number | null;
  created_at: string;
  updated_at: string;
};

export function createLadyaApi() {
  return {
    getSettings: () => request<LadyaSettings>("/ladya/settings/"),
    patchSettings: (data: { ladya_hub_enabled: boolean }) =>
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
      }>,
    ) =>
      request<Laboratory>(`/ladya/laboratories/${id}/`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    deleteLaboratory: (id: number) =>
      request<void>(`/ladya/laboratories/${id}/`, { method: "DELETE" }),

    listPackages: (status?: string) =>
      request<LadyaPackage[]>(
        status ? `/ladya/packages/?status=${encodeURIComponent(status)}` : "/ladya/packages/",
      ),
    getPackage: (id: number) => request<LadyaPackage>(`/ladya/packages/${id}/`),
    createPackage: (data: {
      title: string;
      summary?: string;
      from_laboratory?: number | null;
      to_laboratory?: number | null;
      linked_delivery_task?: number | null;
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

    listIntake: () => request<IntakeRequest[]>("/ladya/intake/"),
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
