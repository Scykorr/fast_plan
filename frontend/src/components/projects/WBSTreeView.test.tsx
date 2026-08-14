import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { WBSNode } from "../../api/projects";
import { WBSTreeView } from "./WBSTreeView";

const mockNodes: WBSNode[] = [
  {
    id: 1,
    code: "1",
    title: "Проект",
    description: "",
    node_type: "deliverable",
    position: 0,
    parent_id: null,
    tracker_id: null,
    tracker_name: null,
    workflow_status_id: null,
    workflow_status_name: null,
    assignee_id: null,
    assignee_name: null,
    custom_values: [],
    schedule: null,
    card_id: null,
    children: [
      {
        id: 2,
        code: "1.1",
        title: "Дизайн",
        description: "",
        node_type: "work_package",
        position: 0,
        parent_id: 1,
        tracker_id: 2,
        tracker_name: "Задача",
        workflow_status_id: 1,
        workflow_status_name: "Новая",
        assignee_id: null,
        assignee_name: null,
        org_unit_id: 3,
        org_unit_name: "Backend",
        obs_role_id: 7,
        obs_role_name: "Developer",
        custom_values: [],
        schedule: {
          id: 1,
          wbs_id: 2,
          name: "Дизайн",
          code: "1.1",
          start_date: "2026-01-01",
          end_date: "2026-01-10",
          duration_days: 10,
          progress: 25,
          is_milestone: false,
        },
        card_id: 5,
        quality: { total: 2, passed: 1, failed: 0, open: 1 },
        children: [],
      },
    ],
  },
];

describe("WBSTreeView", () => {
  it("renders WBS mind map nodes with codes", () => {
    render(
      <WBSTreeView
        nodes={mockNodes}
        onAddChild={vi.fn()}
        onDelete={vi.fn()}
      />,
    );
    expect(screen.getByText("Проект")).toBeInTheDocument();
    expect(screen.getByText("1.1")).toBeInTheDocument();
    expect(screen.getByText("Дизайн")).toBeInTheDocument();
    expect(screen.getByText("Backend")).toBeInTheDocument();
    expect(screen.getByText("Developer")).toBeInTheDocument();
    expect(screen.getByText("QA 1/2")).toBeInTheDocument();
  });

  it("calls onSelect when node double-clicked", () => {
    const onSelect = vi.fn();
    render(
      <WBSTreeView
        nodes={mockNodes}
        onAddChild={vi.fn()}
        onDelete={vi.fn()}
        onSelect={onSelect}
      />,
    );
    fireEvent.doubleClick(screen.getByTestId("wbs-node-2"));
    expect(onSelect).toHaveBeenCalledWith(
      expect.objectContaining({ id: 2, title: "Дизайн" }),
    );
  });

  it("does not open card on single click", () => {
    const onSelect = vi.fn();
    render(
      <WBSTreeView
        nodes={mockNodes}
        onAddChild={vi.fn()}
        onDelete={vi.fn()}
        onSelect={onSelect}
      />,
    );
    fireEvent.click(screen.getByTestId("wbs-node-2"));
    expect(onSelect).not.toHaveBeenCalled();
  });
});
