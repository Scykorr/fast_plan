import { describe, expect, it } from "vitest";

import type { KanbanBoard, KanbanCard } from "../../api/kanban";
import {
  collectKanbanAssignees,
  collectKanbanStatuses,
  filterKanbanBoard,
} from "./kanbanFilters";

function card(partial: Partial<KanbanCard> & Pick<KanbanCard, "id" | "title">): KanbanCard {
  return {
    description: "",
    position: 0,
    due_date: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    wbs_node_id: null,
    assignee_id: null,
    assignee_name: null,
    workflow_status_id: null,
    workflow_status_name: null,
    ...partial,
  };
}

const board: KanbanBoard = {
  id: 1,
  title: "Board",
  position: 0,
  created_at: "2026-01-01T00:00:00Z",
  columns: [
    {
      id: 1,
      title: "Todo",
      position: 0,
      cards: [
        card({
          id: 1,
          title: "A",
          assignee_id: 10,
          assignee_name: "Alice",
          workflow_status_id: 1,
          workflow_status_name: "Новая",
        }),
        card({
          id: 2,
          title: "B",
          assignee_id: 20,
          assignee_name: "Bob",
          workflow_status_id: 2,
          workflow_status_name: "В работе",
        }),
      ],
    },
    {
      id: 2,
      title: "Done",
      position: 1,
      cards: [
        card({
          id: 3,
          title: "C",
          assignee_id: 10,
          assignee_name: "Alice",
          workflow_status_id: 2,
          workflow_status_name: "В работе",
        }),
      ],
    },
  ],
};

describe("kanbanFilters", () => {
  it("filters cards by assignee across columns", () => {
    const filtered = filterKanbanBoard(board, { assigneeId: 10 });
    expect(filtered.columns[0].cards.map((c) => c.id)).toEqual([1]);
    expect(filtered.columns[1].cards.map((c) => c.id)).toEqual([3]);
  });

  it("filters by status", () => {
    const filtered = filterKanbanBoard(board, { statusId: 2 });
    expect(filtered.columns.flatMap((c) => c.cards).map((c) => c.id)).toEqual([
      2, 3,
    ]);
  });

  it("collects options", () => {
    expect(collectKanbanAssignees(board).map((a) => a.name)).toEqual([
      "Alice",
      "Bob",
    ]);
    expect(collectKanbanStatuses(board)).toHaveLength(2);
  });
});
