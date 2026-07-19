import { request, requestForm } from "./client";

export type Attachment = {
  id: number;
  name: string;
  size: number;
  content_type: string;
  url: string | null;
  uploaded_by: number | null;
  uploaded_by_name: string | null;
  wbs_node_id: number | null;
  card_id: number | null;
  created_at: string;
};

export function createAttachmentsApi() {
  return {
    getWbsAttachments: (wbsId: number) =>
      request<Attachment[]>(`/wbs/${wbsId}/attachments/`, {}),

    uploadWbsAttachment: (wbsId: number, file: File) => {
      const form = new FormData();
      form.append("file", file);
      return requestForm<Attachment>(`/wbs/${wbsId}/attachments/`, form);
    },

    getCardAttachments: (cardId: number) =>
      request<Attachment[]>(`/cards/${cardId}/attachments/`, {}),

    uploadCardAttachment: (cardId: number, file: File) => {
      const form = new FormData();
      form.append("file", file);
      return requestForm<Attachment>(`/cards/${cardId}/attachments/`, form);
    },

    deleteAttachment: (id: number) =>
      request<void>(`/attachments/${id}/`, { method: "DELETE" }),
  };
}
