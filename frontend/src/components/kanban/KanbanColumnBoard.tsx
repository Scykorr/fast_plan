import { useDroppable } from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";

import type { KanbanColumn } from "../../api/kanban";
import { KanbanCardItem } from "./KanbanCardItem";

type KanbanColumnBoardProps = {
  column: KanbanColumn;
  onAddCard: (columnId: number) => void;
  onDeleteCard: (cardId: number) => void;
};

export function KanbanColumnBoard({
  column,
  onAddCard,
  onDeleteCard,
}: KanbanColumnBoardProps) {
  const { setNodeRef, isOver } = useDroppable({
    id: `column-${column.id}`,
    data: { type: "column", column },
  });

  const cardIds = column.cards.map((card) => `card-${card.id}`);

  return (
    <div
      className={[
        "flex w-72 shrink-0 flex-col rounded-xl border border-border bg-cream/60",
        isOver ? "ring-2 ring-primary/40" : "",
      ].join(" ")}
    >
      <div className="flex items-center justify-between px-4 py-3">
        <h3 className="text-sm font-semibold text-text">{column.title}</h3>
        <span className="rounded-full bg-surface px-2 py-0.5 text-xs text-text-muted">
          {column.cards.length}
        </span>
      </div>

      <div ref={setNodeRef} className="flex min-h-32 flex-1 flex-col gap-2 px-3 pb-3">
        <SortableContext items={cardIds} strategy={verticalListSortingStrategy}>
          {column.cards.map((card) => (
            <KanbanCardItem key={card.id} card={card} onDelete={onDeleteCard} />
          ))}
        </SortableContext>
      </div>

      <button
        type="button"
        onClick={() => onAddCard(column.id)}
        className="m-3 mt-0 rounded-lg border border-dashed border-border px-3 py-2 text-sm text-text-muted transition-colors hover:border-primary hover:text-primary"
      >
        + Добавить карточку
      </button>
    </div>
  );
}
