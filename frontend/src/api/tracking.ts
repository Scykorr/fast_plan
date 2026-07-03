import { request } from "./client";

export type Tracker = {
  id: number;
  name: string;
  description: string;
  target: "project" | "issue";
  position: number;
  is_default: boolean;
};

export type IssueStatus = {
  id: number;
  name: string;
  position: number;
  is_closed: boolean;
  is_default: boolean;
};

export type CustomFieldEnumeration = {
  id: number;
  name: string;
  position: number;
  is_active: boolean;
  parent_id: number | null;
};

export type CustomField = {
  id: number;
  name: string;
  field_format: string;
  description: string;
  is_required: boolean;
  position: number;
  default_value: string;
  tracker_ids: number[];
  enumerations: CustomFieldEnumeration[];
};

export type CustomValue = {
  field_id: number;
  field_name: string;
  field_format: string;
  value: string;
};

export type TrackingMetadata = {
  trackers: Tracker[];
  statuses: IssueStatus[];
  custom_fields: CustomField[];
};

export function createTrackingApi(token: string) {
  return {
    getMetadata: () =>
      request<TrackingMetadata>("/tracking/metadata/", {}, token),

    createTracker: (body: Partial<Tracker>) =>
      request<Tracker>("/tracking/trackers/", {
        method: "POST",
        body: JSON.stringify(body),
      }, token),

    updateTracker: (id: number, body: Partial<Tracker>) =>
      request<Tracker>(`/tracking/trackers/${id}/`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }, token),

    deleteTracker: (id: number) =>
      request<void>(`/tracking/trackers/${id}/`, { method: "DELETE" }, token),

    createStatus: (body: Partial<IssueStatus>) =>
      request<IssueStatus>("/tracking/statuses/", {
        method: "POST",
        body: JSON.stringify(body),
      }, token),

    updateStatus: (id: number, body: Partial<IssueStatus>) =>
      request<IssueStatus>(`/tracking/statuses/${id}/`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }, token),

    deleteStatus: (id: number) =>
      request<void>(`/tracking/statuses/${id}/`, { method: "DELETE" }, token),

    createCustomField: (body: Partial<CustomField>) =>
      request<CustomField>("/tracking/custom-fields/", {
        method: "POST",
        body: JSON.stringify(body),
      }, token),

    updateCustomField: (id: number, body: Partial<CustomField>) =>
      request<CustomField>(`/tracking/custom-fields/${id}/`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }, token),

    deleteCustomField: (id: number) =>
      request<void>(`/tracking/custom-fields/${id}/`, { method: "DELETE" }, token),
  };
}
