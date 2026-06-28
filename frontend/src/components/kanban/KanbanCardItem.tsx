import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

import type { KanbanCard } from "../../api/kanban";

type KanbanCardItemProps = {
  card: KanbanCard;
  onDelete: (cardId: number) => void;
};

export function KanbanCardItem({ card, onDelete }: KanbanCardItemProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: `card-${card.id}`, data: { type: "card", card } });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={[
        "rounded-lg border border-border bg-surface p-3 shadow-sm",
        isDragging ? "opacity-50 ring-2 ring-primary" : "",
      ].join(" ")}
      {...attributes}
      {...listeners}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium text-text">{card.title}</p>
        <button
          type="button"
          onClick={(event) => {
            event.stopPropagation();
            onDelete(card.id);
          }}
          className="text-xs text-text-muted hover:text-primary"
          aria-label={`Удалить ${card.title}`}
        >
          ×
        </button>
      </div>
      {card.description && (
        <p className="mt-2 text-xs text-text-muted line-clamp-3">
          {card.description}
        </p>
      )}
    </div>
  );
}
