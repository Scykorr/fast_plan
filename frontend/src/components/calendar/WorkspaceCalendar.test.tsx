import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { WorkspaceCalendar } from "./WorkspaceCalendar";

const getBirthdayEvents = vi.fn();
const getMilestoneEvents = vi.fn();

vi.mock("../../api/calendar", () => ({
  createCalendarApi: () => ({
    getBirthdayEvents,
    getMilestoneEvents,
  }),
}));

vi.mock("@fullcalendar/react", () => ({
  default: ({
    events,
    datesSet,
  }: {
    events: Array<{ title: string }>;
    datesSet?: (info: {
      view: { currentStart: Date };
    }) => void;
  }) => {
    queueMicrotask(() => {
      datesSet?.({ view: { currentStart: new Date("2026-07-01T00:00:00") } });
    });
    return (
      <div data-testid="fullcalendar">
        {events.map((event) => (
          <span key={event.title}>{event.title}</span>
        ))}
      </div>
    );
  },
}));

describe("WorkspaceCalendar", () => {
  beforeEach(() => {
    getBirthdayEvents.mockReset();
    getMilestoneEvents.mockReset();
    getBirthdayEvents.mockResolvedValue([
      {
        id: "bday-1",
        title: "ДР: Анна",
        start: "2026-07-10",
        allDay: true,
        extendedProps: { event_type: "birthday" },
      },
    ]);
    getMilestoneEvents.mockResolvedValue([
      {
        id: "ms-1",
        title: "Веха: Релиз",
        start: "2026-07-15",
        allDay: true,
        extendedProps: { event_type: "milestone" },
      },
    ]);
  });

  it("loads and renders birthday and milestone events", async () => {
    render(<WorkspaceCalendar token="test-token" />);

    await waitFor(() => {
      expect(screen.getByText("ДР: Анна")).toBeInTheDocument();
      expect(screen.getByText("Веха: Релиз")).toBeInTheDocument();
    });
    expect(getBirthdayEvents).toHaveBeenCalledWith(2026, 7);
    expect(getMilestoneEvents).toHaveBeenCalledWith(2026, 7);
  });
});
