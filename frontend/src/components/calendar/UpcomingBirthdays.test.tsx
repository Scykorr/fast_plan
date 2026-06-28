import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { UpcomingBirthday } from "../../api/calendar";
import { UpcomingBirthdays } from "./UpcomingBirthdays";

const mockItems: UpcomingBirthday[] = [
  {
    contact_id: 1,
    name: "Анна",
    relation: "подруга",
    birth_date: "1995-03-10",
    next_date: "2026-07-01",
    days_until: 3,
  },
];

describe("UpcomingBirthdays", () => {
  it("renders upcoming birthday items", () => {
    render(<UpcomingBirthdays items={mockItems} />);
    expect(screen.getByText("Анна")).toBeInTheDocument();
    expect(screen.getByText(/подруга/)).toBeInTheDocument();
    expect(screen.getByText("Через 3 дн.")).toBeInTheDocument();
  });

  it("shows empty state", () => {
    render(<UpcomingBirthdays items={[]} />);
    expect(screen.getByText(/Пока нет контактов/)).toBeInTheDocument();
  });
});
