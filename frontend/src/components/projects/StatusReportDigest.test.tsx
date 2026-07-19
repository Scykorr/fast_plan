import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { ProjectStatusReport } from "../../api/projects";
import { StatusReportDigest } from "./StatusReportDigest";

const report: ProjectStatusReport = {
  project: {
    id: 1,
    name: "Alpha",
    status: "active",
    budget: 100000,
    start_date: "2026-01-01",
    end_date: "2026-12-31",
  },
  charter: {
    goals: "",
    success_criteria: "",
    constraints: "",
    assumptions: "",
    updated_at: "2026-07-01T00:00:00Z",
  },
  progress: 42,
  evm: {
    budget: 100000,
    earned_value: 42000,
    planned_value: 50000,
    actual_cost: 40000,
    cpi: 1.05,
    spi: 0.84,
    percent_complete: 42,
  },
  critical_path: {
    activities: [],
    critical_path_ids: [],
    project_duration: 10,
  },
  top_risks: [
    {
      id: 1,
      title: "Delay",
      description: "",
      probability: 3,
      impact: 4,
      score: 12,
      status: "open",
      mitigation: "",
      created_at: "2026-07-01T00:00:00Z",
      updated_at: "2026-07-01T00:00:00Z",
    },
  ],
  stakeholders: [
    {
      id: 1,
      name: "Ann",
      role: "Sponsor",
      interest: 5,
      influence: 5,
      contact_email: "a@example.com",
      notes: "",
      created_at: "2026-07-01T00:00:00Z",
    },
  ],
  milestones: [],
  generated_at: "2026-07-19T10:00:00Z",
};

describe("StatusReportDigest", () => {
  it("renders progress and export actions", () => {
    render(
      <StatusReportDigest
        report={report}
        onExportJson={vi.fn()}
        onExportPdf={vi.fn()}
      />,
    );
    expect(screen.getByText("42%")).toBeInTheDocument();
    expect(screen.getByText("Экспорт JSON")).toBeInTheDocument();
    expect(screen.getByText("Экспорт PDF")).toBeInTheDocument();
    expect(screen.getByText("Delay")).toBeInTheDocument();
  });
});
