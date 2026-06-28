import { request } from "./client";

export type KanbanCard = {
  id: number;
  title: string;
  description: string;
  position: number;
  due_date: string | null;
  created_at: string;
  updated_at: string;
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

export function createKanbanApi(token: string) {
  return {
    getBoards: () => request<KanbanBoardListItem[]>("/boards/", {}, token),

    getBoard: (boardId: number) =>
      request<KanbanBoard>(`/boards/${boardId}/`, {}, token),

    createCard: (
      columnId: number,
      body: { title?: string; description?: string },
    ) =>
      request<KanbanCard>(`/columns/${columnId}/cards/`, {
        method: "POST",
        body: JSON.stringify(body),
      }, token),

    updateCard: (
      cardId: number,
      body: Partial<Pick<KanbanCard, "title" | "description" | "due_date">>,
    ) =>
      request<KanbanCard>(`/cards/${cardId}/`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }, token),

    moveCard: (cardId: number, columnId: number, position: number) =>
      request<KanbanCard>(`/cards/${cardId}/move/`, {
        method: "POST",
        body: JSON.stringify({ column_id: columnId, position }),
      }, token),

    deleteCard: (cardId: number) =>
      request<void>(`/cards/${cardId}/`, { method: "DELETE" }, token),

    createColumn: (boardId: number, title: string) =>
      request<KanbanColumn>(`/boards/${boardId}/columns/`, {
        method: "POST",
        body: JSON.stringify({ title }),
      }, token),
  };
}
