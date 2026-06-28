import { request } from "./client";

export type Contact = {
  id: number;
  name: string;
  relation: string;
  notes: string;
  birth_date: string;
  remind_before_days: number;
  created_at: string;
};

export type CalendarEvent = {
  id: number | string;
  title: string;
  start: string;
  allDay: boolean;
  extendedProps: {
    contact_id?: number;
    relation?: string;
    name?: string;
    activity_id?: number;
    project_id?: number;
    project_name?: string;
    wbs_code?: string;
    event_type?: "birthday" | "milestone";
  };
};

export type UpcomingBirthday = {
  contact_id: number;
  name: string;
  relation: string;
  birth_date: string;
  next_date: string;
  days_until: number;
};

export function createCalendarApi(token: string) {
  return {
    getContacts: () => request<Contact[]>("/contacts/", {}, token),

    createContact: (body: {
      name: string;
      relation?: string;
      notes?: string;
      birth_date: string;
      remind_before_days?: number;
    }) =>
      request<Contact>("/contacts/", {
        method: "POST",
        body: JSON.stringify(body),
      }, token),

    deleteContact: (contactId: number) =>
      request<void>(`/contacts/${contactId}/`, { method: "DELETE" }, token),

    getBirthdayEvents: (year: number, month: number) =>
      request<CalendarEvent[]>(
        `/calendar/birthdays/?year=${year}&month=${month}`,
        {},
        token,
      ),

    getMilestoneEvents: (year: number, month: number) =>
      request<CalendarEvent[]>(
        `/calendar/milestones/?year=${year}&month=${month}`,
        {},
        token,
      ),

    getUpcoming: (limit = 5) =>
      request<UpcomingBirthday[]>(`/calendar/upcoming/?limit=${limit}`, {}, token),
  };
}
