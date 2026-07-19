import { request } from "./client";

export type Notification = {
  id: number;
  notification_type: string;
  title: string;
  message: string;
  link: string;
  is_read: boolean;
  created_at: string;
};

export type NotificationPage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Notification[];
};

export function createNotificationsApi() {
  return {
    getNotifications: (params?: { unreadOnly?: boolean; page?: number }) => {
      const query = new URLSearchParams();
      if (params?.unreadOnly) {
        query.set("unread", "true");
      }
      if (params?.page) {
        query.set("page", String(params.page));
      }
      const suffix = query.toString() ? `?${query.toString()}` : "";
      return request<NotificationPage>(`/notifications/${suffix}`, {});
    },

    markRead: (id: number) =>
      request<Notification>(`/notifications/${id}/`, {
        method: "PATCH",
        body: JSON.stringify({ is_read: true }),
      }),

    markAllRead: () =>
      request<{ updated: number }>("/notifications/mark-all-read/", {
        method: "POST",
      }),
  };
}
