import { useDroppable } from "@dnd-kit/core";
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useEffect, useRef, useState } from "react";

import type { KanbanColumn } from "../../api/kanban";
import { KanbanCardItem } from "./KanbanCardItem";

type KanbanColumnBoardProps = {
  column: KanbanColumn;
  selectedCardId?: number | null;
  onAddCard: (columnId: number) => void;
  onDeleteCard: (cardId: number) => void;
  onRenameColumn: (columnId: number) => void;
  onDeleteColumn: (columnId: number) => void;
  onSelectCard?: (cardId: number) => void;
};

export function KanbanColumnBoard({
  column,
  selectedCardId = null,
  onAddCard,
  onDeleteCard,
  onRenameColumn,
  onDeleteColumn,
  onSelectCard,
}: KanbanColumnBoardProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!menuOpen) {
      return;
    }
    const closeMenu = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as HTMLElement)) {
        setMenuOpen(false);
      }
    };
    window.addEventListener("click", closeMenu);
    return () => window.removeEventListener("click", closeMenu);
  }, [menuOpen]);

  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: `column-${column.id}`,
    data: { type: "column", column },
  });

  const { setNodeRef: setDropRef, isOver } = useDroppable({
    id: `column-drop-${column.id}`,
    data: { type: "column", column },
  });

  const cardIds = column.cards.map((card) => `card-${card.id}`);

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={[
        "flex w-72 shrink-0 flex-col rounded-xl border border-border bg-cream/60",
        isDragging ? "opacity-60 ring-2 ring-secondary" : "",
      ].join(" ")}
    >
      <div className="flex items-center gap-2 px-4 py-3">
        <button
          type="button"
          className="cursor-grab touch-none text-text-muted hover:text-text active:cursor-grabbing"
          aria-label={`Переместить колонку ${column.title}`}
          {...attributes}
          {...listeners}
        >
          ⠿
        </button>
        <h3 className="flex-1 text-sm font-semibold text-text">{column.title}</h3>
        <span className="rounded-full bg-surface px-2 py-0.5 text-xs text-text-muted">
          {column.cards.length}
        </span>
        <div className="relative" ref={menuRef}>
          <button
            type="button"
            className="rounded px-1 text-text-muted hover:bg-surface hover:text-text"
            aria-label={`Меню колонки ${column.title}`}
            onClick={(event) => {
              event.stopPropagation();
              setMenuOpen((open) => !open);
            }}
          >
            ⋮
          </button>
          {menuOpen && (
            <div className="absolute right-0 top-full z-20 mt-1 min-w-36 rounded-lg border border-border bg-surface py-1 shadow-lg">
              <button
                type="button"
                className="block w-full px-3 py-2 text-left text-sm hover:bg-cream"
                onClick={(event) => {
                  event.stopPropagation();
                  setMenuOpen(false);
                  onRenameColumn(column.id);
                }}
              >
                Переименовать
              </button>
              <button
                type="button"
                className="block w-full px-3 py-2 text-left text-sm text-primary hover:bg-cream"
                onClick={(event) => {
                  event.stopPropagation();
                  setMenuOpen(false);
                  onDeleteColumn(column.id);
                }}
              >
                Удалить колонку
              </button>
            </div>
          )}
        </div>
      </div>

      <div
        ref={setDropRef}
        className={[
          "flex min-h-32 flex-1 flex-col gap-2 px-3 pb-3",
          isOver ? "rounded-lg ring-2 ring-primary/40" : "",
        ].join(" ")}
      >
        <SortableContext items={cardIds} strategy={verticalListSortingStrategy}>
          {column.cards.map((card) => (
            <KanbanCardItem
              key={card.id}
              card={card}
              selected={selectedCardId === card.id}
              onDelete={onDeleteCard}
              onSelect={onSelectCard}
            />
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
