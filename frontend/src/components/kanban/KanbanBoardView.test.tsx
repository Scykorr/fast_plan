import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { KanbanBoard } from "../../api/kanban";
import { KanbanBoardView } from "./KanbanBoardView";

const mockBoard: KanbanBoard = {
  id: 1,
  title: "Моя доска",
  position: 0,
  created_at: "2026-01-01T00:00:00Z",
  columns: [
    {
      id: 1,
      title: "К выполнению",
      position: 0,
      cards: [
        {
          id: 1,
          title: "Задача 1",
          description: "Описание",
          position: 0,
          due_date: null,
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
          wbs_node_id: null,
          assignee_id: null,
          assignee_name: null,
          workflow_status_id: null,
          workflow_status_name: null,
        },
      ],
    },
    {
      id: 2,
      title: "Готово",
      position: 1,
      cards: [],
    },
  ],
};

describe("KanbanBoardView", () => {
  it("renders board title and columns", () => {
    render(
      <KanbanBoardView
        board={mockBoard}
        onBoardChange={() => {}}
      />,
    );

    expect(screen.getByRole("heading", { name: "Моя доска" })).toBeInTheDocument();
    expect(screen.getByText("К выполнению")).toBeInTheDocument();
    expect(screen.getByText("Готово")).toBeInTheDocument();
    expect(screen.getByText("Задача 1")).toBeInTheDocument();
  });
});
