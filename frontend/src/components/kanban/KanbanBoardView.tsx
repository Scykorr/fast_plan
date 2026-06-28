import {
  DndContext,
  DragOverlay,
  PointerSensor,
  closestCorners,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { useState } from "react";

import type { KanbanBoard, KanbanCard, KanbanColumn } from "../../api/kanban";
import { createKanbanApi } from "../../api/kanban";
import { KanbanColumnBoard } from "./KanbanColumnBoard";

type KanbanBoardViewProps = {
  board: KanbanBoard;
  token: string;
  onBoardChange: (board: KanbanBoard) => void;
};

function findCard(columns: KanbanColumn[], cardId: number) {
  for (const column of columns) {
    const card = column.cards.find((item) => item.id === cardId);
    if (card) {
      return { column, card };
    }
  }
  return null;
}

function moveCardInBoard(
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
  const movingCard = { ...located.card };
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

function parseDragId(id: string | number) {
  const value = String(id);
  if (value.startsWith("card-")) {
    return { type: "card" as const, id: Number(value.replace("card-", "")) };
  }
  if (value.startsWith("column-")) {
    return { type: "column" as const, id: Number(value.replace("column-", "")) };
  }
  return null;
}

export function KanbanBoardView({
  board,
  token,
  onBoardChange,
}: KanbanBoardViewProps) {
  const kanbanApi = createKanbanApi(token);
  const [activeCard, setActiveCard] = useState<KanbanCard | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    }),
  );

  const handleDragStart = (event: DragStartEvent) => {
    const parsed = parseDragId(event.active.id);
    if (parsed?.type === "card") {
      const located = findCard(board.columns, parsed.id);
      setActiveCard(located?.card ?? null);
    }
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    setActiveCard(null);
    const { active, over } = event;
    if (!over) {
      return;
    }

    const activeParsed = parseDragId(active.id);
    if (!activeParsed || activeParsed.type !== "card") {
      return;
    }

    const overParsed = parseDragId(over.id);
    if (!overParsed) {
      return;
    }

    let targetColumnId: number;
    let targetPosition: number;

    if (overParsed.type === "column") {
      targetColumnId = overParsed.id;
      const column = board.columns.find((item) => item.id === targetColumnId);
      targetPosition = column?.cards.length ?? 0;
    } else {
      const located = findCard(board.columns, overParsed.id);
      if (!located) {
        return;
      }
      targetColumnId = located.column.id;
      targetPosition = located.card.position;
    }

    const previousBoard = board;
    const optimisticBoard = moveCardInBoard(
      board,
      activeParsed.id,
      targetColumnId,
      targetPosition,
    );
    onBoardChange(optimisticBoard);

    try {
      await kanbanApi.moveCard(activeParsed.id, targetColumnId, targetPosition);
      const refreshed = await kanbanApi.getBoard(board.id);
      onBoardChange(refreshed);
    } catch {
      onBoardChange(previousBoard);
    }
  };

  const handleAddCard = async (columnId: number) => {
    const title = window.prompt("Название карточки");
    if (!title?.trim()) {
      return;
    }
    await kanbanApi.createCard(columnId, { title: title.trim() });
    const refreshed = await kanbanApi.getBoard(board.id);
    onBoardChange(refreshed);
  };

  const handleDeleteCard = async (cardId: number) => {
    await kanbanApi.deleteCard(cardId);
    const refreshed = await kanbanApi.getBoard(board.id);
    onBoardChange(refreshed);
  };

  const handleAddColumn = async () => {
    const title = window.prompt("Название колонки");
    if (!title?.trim()) {
      return;
    }
    await kanbanApi.createColumn(board.id, title.trim());
    const refreshed = await kanbanApi.getBoard(board.id);
    onBoardChange(refreshed);
  };

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-text">{board.title}</h1>
          <p className="mt-1 text-sm text-text-muted">
            Перетаскивайте карточки между колонками
          </p>
        </div>
        <button
          type="button"
          onClick={handleAddColumn}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary-hover"
        >
          + Колонка
        </button>
      </div>

      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <div className="flex gap-4 overflow-x-auto pb-4">
          {board.columns.map((column) => (
            <KanbanColumnBoard
              key={column.id}
              column={column}
              onAddCard={handleAddCard}
              onDeleteCard={handleDeleteCard}
            />
          ))}
        </div>

        <DragOverlay>
          {activeCard ? (
            <div className="w-72 rounded-lg border border-primary bg-surface p-3 shadow-lg">
              <p className="text-sm font-medium">{activeCard.title}</p>
            </div>
          ) : null}
        </DragOverlay>
      </DndContext>
    </div>
  );
}
