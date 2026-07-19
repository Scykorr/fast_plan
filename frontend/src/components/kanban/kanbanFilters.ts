import type { KanbanBoard, KanbanCard } from "../../api/kanban";

export type KanbanFilter = {
  assigneeId?: number | null;
  statusId?: number | null;
};

export type FilterOption = {
  id: number;
  name: string;
};

export function cardMatchesFilter(
  card: KanbanCard,
  filter: KanbanFilter,
): boolean {
  if (
    filter.assigneeId != null &&
    card.assignee_id !== filter.assigneeId
  ) {
    return false;
  }
  if (
    filter.statusId != null &&
    card.workflow_status_id !== filter.statusId
  ) {
    return false;
  }
  return true;
}

export function filterKanbanCards(
  cards: KanbanCard[],
  filter: KanbanFilter,
): KanbanCard[] {
  if (filter.assigneeId == null && filter.statusId == null) {
    return cards;
  }
  return cards.filter((card) => cardMatchesFilter(card, filter));
}

export function filterKanbanBoard(
  board: KanbanBoard,
  filter: KanbanFilter,
): KanbanBoard {
  if (filter.assigneeId == null && filter.statusId == null) {
    return board;
  }
  return {
    ...board,
    columns: board.columns.map((column) => ({
      ...column,
      cards: filterKanbanCards(column.cards, filter),
    })),
  };
}

export function collectKanbanAssignees(board: KanbanBoard): FilterOption[] {
  const map = new Map<number, string>();
  for (const column of board.columns) {
    for (const card of column.cards) {
      if (card.assignee_id != null) {
        map.set(
          card.assignee_id,
          card.assignee_name ?? `User #${card.assignee_id}`,
        );
      }
    }
  }
  return [...map.entries()]
    .map(([id, name]) => ({ id, name }))
    .sort((a, b) => a.name.localeCompare(b.name, "ru"));
}

export function collectKanbanStatuses(board: KanbanBoard): FilterOption[] {
  const map = new Map<number, string>();
  for (const column of board.columns) {
    for (const card of column.cards) {
      if (card.workflow_status_id != null) {
        map.set(
          card.workflow_status_id,
          card.workflow_status_name ?? `Status #${card.workflow_status_id}`,
        );
      }
    }
  }
  return [...map.entries()]
    .map(([id, name]) => ({ id, name }))
    .sort((a, b) => a.name.localeCompare(b.name, "ru"));
}
