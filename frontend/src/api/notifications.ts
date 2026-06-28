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

export function createNotificationsApi(token: string) {
  return {
    getNotifications: (unreadOnly = false) =>
      request<Notification[]>(
        unreadOnly ? "/notifications/?unread=true" : "/notifications/",
        {},
        token,
      ),

    markRead: (id: number) =>
      request<Notification>(`/notifications/${id}/`, {
        method: "PATCH",
        body: JSON.stringify({ is_read: true }),
      }, token),
  };
}
