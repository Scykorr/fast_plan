import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { MyTasksPage } from "./MyTasksPage";

const getMyTasks = vi.fn();

vi.mock("../hooks/useWorkspaceApi", () => ({
  useWorkspaceApi: () => ({ getMyTasks }),
}));

vi.mock("../context/WorkspaceContext", () => ({
  useWorkspace: () => ({
    workspaceEpoch: 1,
    activeWorkspace: { id: 1, name: "WS", role: "owner", is_active: true },
  }),
}));

describe("MyTasksPage", () => {
  beforeEach(() => {
    getMyTasks.mockResolvedValue({
      workspace_id: 1,
      assignee_id: 1,
      assignee_name: "Me",
      summary: { total: 1, overdue: 0, due_soon: 0 },
      tasks: [
        {
          wbs_id: 5,
          wbs_code: "1.1",
          title: "Prepare report",
          node_type: "task",
          project_id: 2,
          project_name: "Alpha",
          assignee_id: 1,
          assignee_name: "Me",
          workflow_status_id: 1,
          workflow_status_name: "In progress",
          progress: 10,
          start_date: null,
          end_date: null,
          days_overdue: 0,
          card_id: null,
          board_id: null,
          link: "/projects/2?tab=wbs&node=5",
        },
      ],
    });
  });

  it("lists my tasks", async () => {
    render(
      <MemoryRouter>
        <MyTasksPage />
      </MemoryRouter>,
    );
    expect(await screen.findByText(/Prepare report/)).toBeInTheDocument();
    expect(screen.getByText(/Alpha/)).toBeInTheDocument();
  });
});
