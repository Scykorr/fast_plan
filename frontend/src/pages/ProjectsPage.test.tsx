import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Project } from "../api/projects";
import { ProjectsPage } from "./ProjectsPage";

const { getProjects, getProjectTemplates, deleteProject, projectsApi } =
  vi.hoisted(() => {
    const getProjects = vi.fn();
    const getProjectTemplates = vi.fn();
    const deleteProject = vi.fn();
    return {
      getProjects,
      getProjectTemplates,
      deleteProject,
      projectsApi: {
        getProjects,
        getProjectTemplates,
        deleteProject,
        createProject: vi.fn(),
        createProjectTemplate: vi.fn(),
      },
    };
  });

vi.mock("../hooks/useProjectsApi", () => ({
  useProjectsApi: () => projectsApi,
}));

const workspaceState = {
  activeWorkspace: {
    id: 1,
    name: "WS",
    role: "owner" as string,
    is_active: true,
  },
};

vi.mock("../context/WorkspaceContext", () => ({
  useWorkspace: () => workspaceState,
}));

const sampleProject: Project = {
  id: 7,
  name: "Alpha",
  description: "First project",
  status: "planning",
  start_date: null,
  end_date: null,
  budget: 0,
  manager: null,
  tracker_id: null,
  workflow_status_id: null,
  custom_values: [],
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  wbs_count: 2,
  progress: 10,
  board_id: 1,
};

describe("ProjectsPage", () => {
  beforeEach(() => {
    workspaceState.activeWorkspace.role = "owner";
    getProjects.mockReset();
    getProjectTemplates.mockReset();
    deleteProject.mockReset();
    getProjects.mockResolvedValue([sampleProject]);
    getProjectTemplates.mockResolvedValue([]);
    deleteProject.mockResolvedValue(undefined);
  });

  it("deletes a project after confirmation", async () => {
    render(
      <MemoryRouter>
        <ProjectsPage />
      </MemoryRouter>,
    );

    expect(
      await screen.findByRole("heading", { name: "Alpha" }),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Удалить" }));
    expect(await screen.findByRole("alertdialog")).toBeInTheDocument();

    const confirmButtons = screen.getAllByRole("button", { name: "Удалить" });
    fireEvent.click(confirmButtons[confirmButtons.length - 1]);

    await waitFor(() => {
      expect(deleteProject).toHaveBeenCalledWith(7);
    });
    await waitFor(() => {
      expect(
        screen.queryByRole("heading", { name: "Alpha" }),
      ).not.toBeInTheDocument();
    });
  });

  it("hides delete for viewers", async () => {
    workspaceState.activeWorkspace.role = "viewer";
    render(
      <MemoryRouter>
        <ProjectsPage />
      </MemoryRouter>,
    );

    expect(
      await screen.findByRole("heading", { name: "Alpha" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Удалить" }),
    ).not.toBeInTheDocument();
  });
});
