import dayGridPlugin from "@fullcalendar/daygrid";
import FullCalendar from "@fullcalendar/react";
import { useCallback, useState } from "react";
import type { DatesSetArg, EventInput } from "@fullcalendar/core";

import type { ProjectCalendarEvent } from "../../api/projects";
import { createProjectsApi } from "../../api/projects";

type ProjectCalendarProps = {
  projectId: number;
  token: string;
};

export function ProjectCalendar({ projectId, token }: ProjectCalendarProps) {
  const projectsApi = createProjectsApi(token);
  const [events, setEvents] = useState<EventInput[]>([]);
  const [loading, setLoading] = useState(false);

  const loadEvents = useCallback(
    async (year: number, month: number) => {
      setLoading(true);
      try {
        const data = await projectsApi.getProjectCalendar(projectId, year, month);
        setEvents(
          data.map((event: ProjectCalendarEvent) => ({
            id: String(event.id),
            title: event.title,
            start: event.start,
            allDay: event.allDay,
            extendedProps: event.extendedProps,
            color: "#6B8F71",
            textColor: "#2D2926",
          })),
        );
      } finally {
        setLoading(false);
      }
    },
    [projectsApi, projectId],
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
          eventColor="#6B8F71"
          eventTextColor="#2D2926"
        />
      </div>
    </div>
  );
}
