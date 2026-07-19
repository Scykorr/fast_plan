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
import {
  SortableContext,
  horizontalListSortingStrategy,
} from "@dnd-kit/sortable";
import { useState } from "react";

import type { KanbanBoard, KanbanCard, KanbanColumn } from "../../api/kanban";
import { createKanbanApi } from "../../api/kanban";
import { parseApiError } from "../../api/errors";
import { useConfirm } from "../../hooks/useConfirm";
import { KanbanColumnBoard } from "./KanbanColumnBoard";
import {
  filterKanbanBoard,
  type KanbanFilter,
} from "./kanbanFilters";
import {
  findCard,
  moveCardInBoard,
  moveColumnInBoard,
  parseDragId,
  sortedColumns,
} from "./kanbanBoardLogic";

type KanbanBoardViewProps = {
  board: KanbanBoard;
  onBoardChange: (board: KanbanBoard) => void;
  selectedCardId?: number | null;
  filter?: KanbanFilter;
  onSelectCard?: (cardId: number) => void;
};

export function KanbanBoardView({
  board,
  onBoardChange,
  selectedCardId = null,
  filter,
  onSelectCard,
}: KanbanBoardViewProps) {
  const kanbanApi = createKanbanApi();
  const { confirm, dialog: confirmDialog } = useConfirm();
  const [activeCard, setActiveCard] = useState<KanbanCard | null>(null);
  const [activeColumn, setActiveColumn] = useState<KanbanColumn | null>(null);
  const [showColumnForm, setShowColumnForm] = useState(false);
  const [columnTitle, setColumnTitle] = useState("");
  const [error, setError] = useState("");
  const [savingColumn, setSavingColumn] = useState(false);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    }),
  );

  const displayBoard = filter ? filterKanbanBoard(board, filter) : board;
  const columns = sortedColumns(displayBoard.columns);
  const columnIds = columns.map((column) => `column-${column.id}`);

  const handleDragStart = (event: DragStartEvent) => {
    const parsed = parseDragId(event.active.id);
    if (parsed?.type === "card") {
      const located = findCard(board.columns, parsed.id);
      setActiveCard(located?.card ?? null);
      setActiveColumn(null);
      return;
    }
    if (parsed?.type === "column") {
      const column = board.columns.find((item) => item.id === parsed.id);
      setActiveColumn(column ?? null);
      setActiveCard(null);
    }
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    const previousBoard = board;
    setActiveCard(null);
    setActiveColumn(null);

    const { active, over } = event;
    if (!over) {
      return;
    }

    const activeParsed = parseDragId(active.id);
    const overParsed = parseDragId(over.id);
    if (!activeParsed || !overParsed) {
      return;
    }

    if (activeParsed.type === "column" && overParsed.type === "column") {
      const ordered = sortedColumns(board.columns);
      const oldIndex = ordered.findIndex((column) => column.id === activeParsed.id);
      const newIndex = ordered.findIndex((column) => column.id === overParsed.id);
      if (oldIndex < 0 || newIndex < 0 || oldIndex === newIndex) {
        return;
      }

      const optimisticBoard = moveColumnInBoard(board, activeParsed.id, newIndex);
      onBoardChange(optimisticBoard);

      try {
        await kanbanApi.moveColumn(activeParsed.id, newIndex);
        onBoardChange(await kanbanApi.getBoard(board.id));
      } catch {
        onBoardChange(previousBoard);
      }
      return;
    }

    if (activeParsed.type !== "card") {
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

    const optimisticBoard = moveCardInBoard(
      board,
      activeParsed.id,
      targetColumnId,
      targetPosition,
    );
    onBoardChange(optimisticBoard);

    try {
      await kanbanApi.moveCard(activeParsed.id, targetColumnId, targetPosition);
      onBoardChange(await kanbanApi.getBoard(board.id));
    } catch {
      onBoardChange(previousBoard);
    }
  };

  const handleAddCard = async (columnId: number, title: string) => {
    try {
      await kanbanApi.createCard(columnId, { title });
      onBoardChange(await kanbanApi.getBoard(board.id));
    } catch (err) {
      setError(parseApiError(err, "Не удалось создать карточку"));
      throw err;
    }
  };

  const handleDeleteCard = async (cardId: number) => {
    if (!(await confirm("Удалить карточку?"))) {
      return;
    }
    try {
      await kanbanApi.deleteCard(cardId);
      onBoardChange(await kanbanApi.getBoard(board.id));
    } catch (err) {
      setError(parseApiError(err, "Не удалось удалить карточку"));
    }
  };

  const handleAddColumn = async () => {
    if (!columnTitle.trim()) {
      setError("Укажите название колонки");
      return;
    }
    setSavingColumn(true);
    setError("");
    try {
      await kanbanApi.createColumn(board.id, columnTitle.trim());
      setColumnTitle("");
      setShowColumnForm(false);
      onBoardChange(await kanbanApi.getBoard(board.id));
    } catch (err) {
      setError(parseApiError(err, "Не удалось создать колонку"));
    } finally {
      setSavingColumn(false);
    }
  };

  const handleRenameColumn = async (columnId: number, title: string) => {
    try {
      await kanbanApi.updateColumn(columnId, { title });
      onBoardChange(await kanbanApi.getBoard(board.id));
    } catch (err) {
      setError(parseApiError(err, "Не удалось переименовать колонку"));
      throw err;
    }
  };

  const handleDeleteColumn = async (columnId: number) => {
    const column = board.columns.find((item) => item.id === columnId);
    if (!column) {
      return;
    }
    const cardLabel =
      column.cards.length === 1
        ? "1 карточку"
        : `${column.cards.length} карточек`;
    const message =
      column.cards.length > 0
        ? `Удалить колонку «${column.title}» и ${cardLabel}?`
        : `Удалить колонку «${column.title}»?`;
    if (!(await confirm(message))) {
      return;
    }
    try {
      await kanbanApi.deleteColumn(columnId);
      onBoardChange(await kanbanApi.getBoard(board.id));
    } catch (err) {
      setError(parseApiError(err, "Не удалось удалить колонку"));
    }
  };

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold text-text">{board.title}</h1>
          <p className="mt-1 text-sm text-text-muted">
            Перетаскивайте карточки и колонки
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowColumnForm((value) => !value)}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary-hover"
        >
          {showColumnForm ? "Скрыть" : "+ Колонка"}
        </button>
      </div>

      {showColumnForm && (
        <div className="mb-4 flex max-w-md flex-wrap items-end gap-2 rounded-xl border border-dashed border-border bg-surface p-3">
          <div className="min-w-48 flex-1">
            <label htmlFor="column-title" className="mb-1 block text-xs font-medium">
              Название колонки
            </label>
            <input
              id="column-title"
              value={columnTitle}
              onChange={(e) => setColumnTitle(e.target.value)}
              className="w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm"
              autoFocus
            />
          </div>
          <button
            type="button"
            disabled={savingColumn}
            onClick={() => void handleAddColumn()}
            className="rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"
          >
            {savingColumn ? "..." : "Добавить"}
          </button>
        </div>
      )}

      {error && (
        <p className="mb-3 text-sm text-primary" role="alert">
          {error}
        </p>
      )}

      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <SortableContext items={columnIds} strategy={horizontalListSortingStrategy}>
          <div className="flex gap-4 overflow-x-auto pb-4">
            {columns.map((column) => (
              <KanbanColumnBoard
                key={column.id}
                column={column}
                selectedCardId={selectedCardId}
                onAddCard={handleAddCard}
                onDeleteCard={handleDeleteCard}
                onRenameColumn={handleRenameColumn}
                onDeleteColumn={handleDeleteColumn}
                onSelectCard={onSelectCard}
              />
            ))}
          </div>
        </SortableContext>

        <DragOverlay>
          {activeCard ? (
            <div className="w-72 rounded-lg border border-primary bg-surface p-3 shadow-lg">
              <p className="text-sm font-medium">{activeCard.title}</p>
            </div>
          ) : null}
          {activeColumn ? (
            <div className="w-72 rounded-xl border border-secondary bg-cream/80 p-4 shadow-lg">
              <p className="text-sm font-semibold text-text">{activeColumn.title}</p>
            </div>
          ) : null}
        </DragOverlay>
      </DndContext>
      {confirmDialog}
    </div>
  );
}
