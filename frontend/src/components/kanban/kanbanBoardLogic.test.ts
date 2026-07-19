import { describe, expect, it } from "vitest";

import type { KanbanBoard } from "../../api/kanban";
import {
  moveCardInBoard,
  moveColumnInBoard,
  parseDragId,
} from "./kanbanBoardLogic";

const mockBoard: KanbanBoard = {
  id: 1,
  title: "Моя доска",
  position: 0,
  created_at: "2026-01-01T00:00:00Z",
  columns: [
    {
      id: 10,
      title: "К выполнению",
      position: 0,
      cards: [
        {
          id: 1,
          title: "Первая",
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
        },
        {
          id: 2,
          title: "Вторая",
          description: "",
          position: 1,
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
      id: 20,
      title: "В работе",
      position: 1,
      cards: [],
    },
    {
      id: 30,
      title: "Готово",
      position: 2,
      cards: [],
    },
  ],
};

describe("kanbanBoardLogic", () => {
  it("reorders a card within the same column", () => {
    const next = moveCardInBoard(mockBoard, 2, 10, 0);
    const cards = next.columns.find((column) => column.id === 10)?.cards ?? [];
    expect(cards.map((card) => card.id)).toEqual([2, 1]);
    expect(cards.map((card) => card.position)).toEqual([0, 1]);
  });

  it("moves a card to another column", () => {
    const next = moveCardInBoard(mockBoard, 1, 20, 0);
    const source = next.columns.find((column) => column.id === 10)?.cards ?? [];
    const target = next.columns.find((column) => column.id === 20)?.cards ?? [];
    expect(source.map((card) => card.id)).toEqual([2]);
    expect(target.map((card) => card.id)).toEqual([1]);
    expect(target[0].position).toBe(0);
  });

  it("reorders columns", () => {
    const next = moveColumnInBoard(mockBoard, 30, 0);
    expect(next.columns.map((column) => column.id)).toEqual([30, 10, 20]);
    expect(next.columns.map((column) => column.position)).toEqual([0, 1, 2]);
  });

  it("parses drag ids for cards and columns", () => {
    expect(parseDragId("card-15")).toEqual({ type: "card", id: 15 });
    expect(parseDragId("column-7")).toEqual({ type: "column", id: 7 });
    expect(parseDragId("column-drop-7")).toEqual({ type: "column", id: 7 });
    expect(parseDragId("unknown")).toBeNull();
  });
});
