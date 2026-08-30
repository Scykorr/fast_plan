import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { TasksPage } from "./TasksPage";

const getTasks = vi.fn();
const getProjects = vi.fn();
const getMembers = vi.fn();
const getMetadata = vi.fn();

vi.mock("../hooks/useWorkspaceApi", () => ({
  useWorkspaceApi: () => ({ getTasks, getMembers }),
}));

vi.mock("../hooks/useProjectsApi", () => ({
  useProjectsApi: () => ({ getProjects }),
}));

vi.mock("../hooks/useTrackingApi", () => ({
  useTrackingApi: () => ({ getMetadata }),
}));

vi.mock("../context/WorkspaceContext", () => ({
  useWorkspace: () => ({
    workspaceEpoch: 1,
    activeWorkspace: { id: 1, name: "WS", role: "owner", is_active: true },
  }),
}));

vi.mock("../context/AuthContext", () => ({
  useAuth: () => ({ user: { id: 1, email: "me@example.com" } }),
}));

describe("TasksPage", () => {
  beforeEach(() => {
    getProjects.mockResolvedValue([{ id: 2, name: "Alpha" }]);
    getMembers.mockResolvedValue([
      { id: 1, user_id: 1, email: "me@example.com", username: "me", role: "owner" },
    ]);
    getMetadata.mockResolvedValue({
      trackers: [],
      statuses: [{ id: 1, name: "Новая", is_closed: false, is_default: true, position: 0 }],
      custom_fields: [],
    });
    getTasks.mockResolvedValue({
      workspace_id: 1,
      summary: { total: 1, overdue: 0, due_soon: 0, returned: 1 },
      tasks: [
        {
          wbs_id: 5,
          wbs_code: "1.1",
          title: "Prepare report",
          node_type: "work_package",
          project_id: 2,
          project_name: "Alpha",
          assignee_id: 1,
          assignee_name: "me@example.com",
          workflow_status_id: 1,
          workflow_status_name: "Новая",
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

  it("opens task card on row click", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <TasksPage />
      </MemoryRouter>,
    );
    expect(await screen.findByText("Prepare report")).toBeInTheDocument();
    await user.click(screen.getByText("Prepare report"));
    expect(screen.getByRole("heading", { name: "Prepare report" })).toBeInTheDocument();
    expect(screen.getByText("Открыть в проекте")).toBeInTheDocument();
  });
});
