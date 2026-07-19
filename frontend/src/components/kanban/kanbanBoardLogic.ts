import { arrayMove } from "@dnd-kit/sortable";

import type { KanbanBoard, KanbanCard, KanbanColumn } from "../../api/kanban";

export function sortedColumns(columns: KanbanColumn[]) {
  return [...columns].sort((left, right) => left.position - right.position);
}

export function findCard(columns: KanbanColumn[], cardId: number) {
  for (const column of columns) {
    const card = column.cards.find((item) => item.id === cardId);
    if (card) {
      return { column, card };
    }
  }
  return null;
}

export function moveCardInBoard(
  board: KanbanBoard,
  cardId: number,
  targetColumnId: number,
  targetPosition: number,
): KanbanBoard {
  const located = findCard(board.columns, cardId);
  if (!located) {
    return board;
  }

  const columns = board.columns.map((column) => ({
    ...column,
    cards: [...column.cards],
  }));

  const sourceColumn = columns.find((column) => column.id === located.column.id);
  const destinationColumn = columns.find((column) => column.id === targetColumnId);
  if (!sourceColumn || !destinationColumn) {
    return board;
  }

  sourceColumn.cards = sourceColumn.cards.filter((card) => card.id !== cardId);
  const movingCard: KanbanCard = { ...located.card };
  const insertAt = Math.min(targetPosition, destinationColumn.cards.length);
  destinationColumn.cards.splice(insertAt, 0, movingCard);

  columns.forEach((column) => {
    column.cards = column.cards.map((card, index) => ({
      ...card,
      position: index,
    }));
  });

  return { ...board, columns };
}

export function moveColumnInBoard(
  board: KanbanBoard,
  columnId: number,
  targetPosition: number,
): KanbanBoard {
  const columns = sortedColumns(board.columns);
  const oldIndex = columns.findIndex((column) => column.id === columnId);
  if (oldIndex < 0) {
    return board;
  }

  const reordered = arrayMove(columns, oldIndex, targetPosition).map(
    (column, index) => ({
      ...column,
      position: index,
    }),
  );

  return { ...board, columns: reordered };
}

export function parseDragId(id: string | number) {
  const value = String(id);
  if (value.startsWith("card-")) {
    return { type: "card" as const, id: Number(value.replace("card-", "")) };
  }
  if (value.startsWith("column-drop-")) {
    return {
      type: "column" as const,
      id: Number(value.replace("column-drop-", "")),
    };
  }
  if (value.startsWith("column-")) {
    return { type: "column" as const, id: Number(value.replace("column-", "")) };
  }
  return null;
}
