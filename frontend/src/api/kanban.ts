import { request } from "./client";

export type KanbanCard = {
  id: number;
  title: string;
  description: string;
  position: number;
  due_date: string | null;
  created_at: string;
  updated_at: string;
  wbs_node_id: number | null;
  assignee_id: number | null;
  assignee_name: string | null;
  workflow_status_id: number | null;
  workflow_status_name: string | null;
};

export type KanbanColumn = {
  id: number;
  title: string;
  position: number;
  cards: KanbanCard[];
};

export type KanbanBoard = {
  id: number;
  title: string;
  position: number;
  created_at: string;
  columns: KanbanColumn[];
};

export type KanbanBoardListItem = {
  id: number;
  title: string;
  position: number;
  created_at: string;
};

export type BoardFlowAnalytics = {
  board_id: number;
  done_column_id?: number;
  burndown: Array<{ date: string; remaining: number; ideal: number }>;
  velocity: Array<{ week_start: string; completed: number }>;
};

export function createKanbanApi() {
  return {
    getBoards: () => request<KanbanBoardListItem[]>("/boards/", {}),

    getBoard: (boardId: number) =>
      request<KanbanBoard>(`/boards/${boardId}/`, {}),

    getBoardAnalytics: (boardId: number, days = 14) =>
      request<BoardFlowAnalytics>(
        `/boards/${boardId}/analytics/?days=${days}`,
        {},
      ),

    createCard: (
      columnId: number,
      body: { title?: string; description?: string },
    ) =>
      request<KanbanCard>(`/columns/${columnId}/cards/`, {
        method: "POST",
        body: JSON.stringify(body),
      }),

    updateCard: (
      cardId: number,
      body: Partial<Pick<KanbanCard, "title" | "description" | "due_date">>,
    ) =>
      request<KanbanCard>(`/cards/${cardId}/`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),

    moveCard: (cardId: number, columnId: number, position: number) =>
      request<KanbanCard>(`/cards/${cardId}/move/`, {
        method: "POST",
        body: JSON.stringify({ column_id: columnId, position }),
      }),

    deleteCard: (cardId: number) =>
      request<void>(`/cards/${cardId}/`, { method: "DELETE" }),

    createColumn: (boardId: number, title: string) =>
      request<KanbanColumn>(`/boards/${boardId}/columns/`, {
        method: "POST",
        body: JSON.stringify({ title }),
      }),

    moveColumn: (columnId: number, position: number) =>
      request<KanbanColumn>(`/columns/${columnId}/`, {
        method: "PATCH",
        body: JSON.stringify({ position }),
      }),

    updateColumn: (columnId: number, body: { title: string }) =>
      request<KanbanColumn>(`/columns/${columnId}/`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),

    deleteColumn: (columnId: number) =>
      request<void>(`/columns/${columnId}/`, { method: "DELETE" }),
  };
}
