import { useDroppable } from "@dnd-kit/core";
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useEffect, useRef, useState, type FormEvent } from "react";

import type { KanbanColumn } from "../../api/kanban";
import { KanbanCardItem } from "./KanbanCardItem";

type KanbanColumnBoardProps = {
  column: KanbanColumn;
  selectedCardId?: number | null;
  onAddCard: (columnId: number, title: string) => Promise<void> | void;
  onDeleteCard: (cardId: number) => void;
  onRenameColumn: (columnId: number, title: string) => Promise<void> | void;
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
  const [addingCard, setAddingCard] = useState(false);
  const [renaming, setRenaming] = useState(false);
  const [cardTitle, setCardTitle] = useState("");
  const [columnTitle, setColumnTitle] = useState(column.title);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setColumnTitle(column.title);
  }, [column.title]);

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

  const submitCard = async (event: FormEvent) => {
    event.preventDefault();
    if (!cardTitle.trim()) {
      setError("Укажите название карточки");
      return;
    }
    setLoading(true);
    setError("");
    try {
      await onAddCard(column.id, cardTitle.trim());
      setCardTitle("");
      setAddingCard(false);
    } catch {
      setError("Не удалось создать карточку");
    } finally {
      setLoading(false);
    }
  };

  const submitRename = async (event: FormEvent) => {
    event.preventDefault();
    if (!columnTitle.trim()) {
      setError("Укажите название колонки");
      return;
    }
    if (columnTitle.trim() === column.title) {
      setRenaming(false);
      return;
    }
    setLoading(true);
    setError("");
    try {
      await onRenameColumn(column.id, columnTitle.trim());
      setRenaming(false);
      setMenuOpen(false);
    } catch {
      setError("Не удалось переименовать колонку");
    } finally {
      setLoading(false);
    }
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
        {renaming ? (
          <form onSubmit={submitRename} className="flex flex-1 items-center gap-1" noValidate>
            <input
              value={columnTitle}
              onChange={(e) => setColumnTitle(e.target.value)}
              className="w-full rounded border border-border bg-surface px-2 py-1 text-sm"
              autoFocus
              aria-label="Название колонки"
            />
            <button
              type="submit"
              disabled={loading}
              className="rounded bg-primary px-2 py-1 text-xs text-white"
            >
              OK
            </button>
          </form>
        ) : (
          <h3 className="flex-1 text-sm font-semibold text-text">{column.title}</h3>
        )}
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
                  setRenaming(true);
                  setColumnTitle(column.title);
                  setMenuOpen(false);
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

      {addingCard ? (
        <form onSubmit={submitCard} className="m-3 mt-0 space-y-2" noValidate>
          <input
            value={cardTitle}
            onChange={(e) => setCardTitle(e.target.value)}
            className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm"
            placeholder="Название карточки"
            autoFocus
            aria-label="Название карточки"
          />
          {error && (
            <p className="text-xs text-primary" role="alert">
              {error}
            </p>
          )}
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={loading}
              className="rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-60"
            >
              Добавить
            </button>
            <button
              type="button"
              onClick={() => {
                setAddingCard(false);
                setCardTitle("");
                setError("");
              }}
              className="rounded-lg border border-border px-3 py-1.5 text-xs text-text-muted"
            >
              Отмена
            </button>
          </div>
        </form>
      ) : (
        <button
          type="button"
          onClick={() => setAddingCard(true)}
          className="m-3 mt-0 rounded-lg border border-dashed border-border px-3 py-2 text-sm text-text-muted transition-colors hover:border-primary hover:text-primary"
        >
          + Добавить карточку
        </button>
      )}
    </div>
  );
}
