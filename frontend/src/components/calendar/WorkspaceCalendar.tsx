import dayGridPlugin from "@fullcalendar/daygrid";
import FullCalendar from "@fullcalendar/react";
import { useCallback, useState } from "react";
import type { DatesSetArg, EventInput } from "@fullcalendar/core";

import type { CalendarEvent } from "../../api/calendar";
import { createCalendarApi } from "../../api/calendar";

type WorkspaceCalendarProps = {
  token: string;
  refreshKey?: number;
  showBirthdays?: boolean;
  showMilestones?: boolean;
};

export function WorkspaceCalendar({
  token,
  refreshKey = 0,
  showBirthdays = true,
  showMilestones = true,
}: WorkspaceCalendarProps) {
  const calendarApi = createCalendarApi(token);
  const [events, setEvents] = useState<EventInput[]>([]);
  const [loading, setLoading] = useState(false);

  const loadEvents = useCallback(
    async (year: number, month: number) => {
      setLoading(true);
      try {
        const requests: Promise<CalendarEvent[]>[] = [];
        if (showBirthdays) {
          requests.push(calendarApi.getBirthdayEvents(year, month));
        }
        if (showMilestones) {
          requests.push(calendarApi.getMilestoneEvents(year, month));
        }
        const batches = await Promise.all(requests);
        setEvents(
          batches.flat().map((event) => ({
            id: String(event.id),
            title: event.title,
            start: event.start,
            allDay: event.allDay,
            extendedProps: event.extendedProps,
            color:
              event.extendedProps.event_type === "milestone" ? "#6B8F71" : "#E8A838",
            textColor: "#2D2926",
          })),
        );
      } finally {
        setLoading(false);
      }
    },
    [calendarApi, showBirthdays, showMilestones],
  );

  const handleDatesSet = useCallback(
    (info: DatesSetArg) => {
      const current = info.view.currentStart;
      void loadEvents(current.getFullYear(), current.getMonth() + 1);
    },
    [loadEvents],
  );

  return (
    <div className="relative">
      {loading && (
        <div className="absolute right-3 top-3 z-10 rounded-lg bg-surface px-3 py-1 text-xs text-text-muted shadow-sm">
          Загрузка...
        </div>
      )}
      <div className="birthday-calendar rounded-xl border border-border bg-surface p-4">
        <FullCalendar
          key={`${refreshKey}-${showBirthdays}-${showMilestones}`}
          plugins={[dayGridPlugin]}
          initialView="dayGridMonth"
          locale="ru"
          headerToolbar={{
            left: "prev,next today",
            center: "title",
            right: "",
          }}
          height="auto"
          events={events}
          datesSet={handleDatesSet}
          eventColor="#E8A838"
          eventTextColor="#2D2926"
        />
      </div>
    </div>
  );
}
