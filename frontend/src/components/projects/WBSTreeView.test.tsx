import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
        children: [],
      },
    ],
  },
];

describe("WBSTreeView", () => {
  it("renders WBS nodes with codes", () => {
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
  });

  it("calls onSelect when node clicked", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(
      <WBSTreeView
        nodes={mockNodes}
        onAddChild={vi.fn()}
        onDelete={vi.fn()}
        onSelect={onSelect}
      />,
    );
    await user.click(screen.getByText("Дизайн"));
    expect(onSelect).toHaveBeenCalledWith(
      expect.objectContaining({ id: 2, title: "Дизайн" }),
    );
  });
});
