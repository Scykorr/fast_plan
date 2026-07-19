import { type FormEvent, useState } from "react";

import type { WorkItemComment } from "../../api/projects";

type Props = {
  comments: WorkItemComment[];
  onAdd: (body: string, kind: "comment" | "decision") => void | Promise<void>;
  onDelete?: (id: number) => void | Promise<void>;
  canDelete?: boolean;
};

export function CommentThread({
  comments,
  onAdd,
  onDelete,
  canDelete = false,
}: Props) {
  const [body, setBody] = useState("");
  const [kind, setKind] = useState<"comment" | "decision">("comment");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    const trimmed = body.trim();
    if (!trimmed || submitting) {
      return;
    }
    setSubmitting(true);
    try {
      await onAdd(trimmed, kind);
      setBody("");
      setKind("comment");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="rounded-xl border border-border bg-surface p-5">
      <h3 className="mb-4 text-lg font-semibold text-text">Комментарии</h3>

      <form onSubmit={(event) => void handleSubmit(event)} className="space-y-3">
        <label className="block text-sm text-text-muted">
          Текст
          <textarea
            value={body}
            onChange={(event) => setBody(event.target.value)}
            rows={3}
            className="mt-1 w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm text-text"
            placeholder="Напишите комментарий или решение..."
            aria-label="Текст комментария"
          />
        </label>
        <div className="flex flex-wrap items-end gap-3">
          <label className="block text-sm text-text-muted">
            Тип
            <select
              value={kind}
              onChange={(event) =>
                setKind(event.target.value as "comment" | "decision")
              }
              className="mt-1 block rounded-lg border border-border bg-cream px-3 py-2 text-sm text-text"
              aria-label="Тип комментария"
            >
              <option value="comment">comment</option>
              <option value="decision">decision</option>
            </select>
          </label>
          <button
            type="submit"
            disabled={submitting || !body.trim()}
            className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50"
          >
            Отправить
          </button>
        </div>
      </form>

      <ul className="mt-5 space-y-3">
        {comments.length === 0 && (
          <li className="text-sm text-text-muted">Пока нет комментариев</li>
        )}
        {comments.map((comment) => (
          <li
            key={comment.id}
            className="rounded-lg border border-border px-3 py-2"
          >
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-medium text-text">
                {comment.author_name}
              </span>
              <span
                className={[
                  "rounded-md px-2 py-0.5 text-xs font-medium",
                  comment.kind === "decision"
                    ? "bg-primary/10 text-primary"
                    : "bg-cream text-text-muted",
                ].join(" ")}
              >
                {comment.kind}
              </span>
              <span className="text-xs text-text-muted">
                {new Date(comment.created_at).toLocaleString("ru-RU")}
              </span>
              {canDelete && onDelete && (
                <button
                  type="button"
                  onClick={() => void onDelete(comment.id)}
                  className="ml-auto text-xs text-primary hover:underline"
                >
                  Удалить
                </button>
              )}
            </div>
            <p className="mt-2 whitespace-pre-wrap text-sm text-text">
              {comment.body}
            </p>
          </li>
        ))}
      </ul>
    </div>
  );
}
