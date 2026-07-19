import { type FormEvent, useMemo, useRef, useState } from "react";

import type { WorkItemComment } from "../../api/projects";
import type { WorkspaceMember } from "../../api/workspace";

type Props = {
  comments: WorkItemComment[];
  members?: WorkspaceMember[];
  onAdd: (body: string, kind: "comment" | "decision") => void | Promise<void>;
  onDelete?: (id: number) => void | Promise<void>;
  canDelete?: boolean;
};

function findMentionQuery(text: string, cursor: number): string | null {
  const upToCursor = text.slice(0, cursor);
  const match = /(?:^|\s)@(\w*)$/.exec(upToCursor);
  return match ? match[1] : null;
}

export function CommentThread({
  comments,
  members = [],
  onAdd,
  onDelete,
  canDelete = false,
}: Props) {
  const [body, setBody] = useState("");
  const [kind, setKind] = useState<"comment" | "decision">("comment");
  const [submitting, setSubmitting] = useState(false);
  const [mentionQuery, setMentionQuery] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const mentionSuggestions = useMemo(() => {
    if (mentionQuery == null) {
      return [];
    }
    const query = mentionQuery.toLowerCase();
    return members
      .filter((member) => member.username.toLowerCase().startsWith(query))
      .slice(0, 5);
  }, [mentionQuery, members]);

  const updateMentionState = (value: string, cursor: number) => {
    setMentionQuery(findMentionQuery(value, cursor));
  };

  const handleBodyChange = (event: { target: HTMLTextAreaElement }) => {
    const { value, selectionStart } = event.target;
    setBody(value);
    updateMentionState(value, selectionStart ?? value.length);
  };

  const applyMention = (username: string) => {
    const textarea = textareaRef.current;
    const cursor = textarea?.selectionStart ?? body.length;
    const upToCursor = body.slice(0, cursor);
    const match = /(?:^|\s)@(\w*)$/.exec(upToCursor);
    if (!match) {
      return;
    }
    const mentionStart = upToCursor.length - match[0].length + (match[0].startsWith(" ") ? 1 : 0);
    const before = body.slice(0, mentionStart);
    const after = body.slice(cursor);
    const nextValue = `${before}@${username} ${after}`;
    setBody(nextValue);
    setMentionQuery(null);
    requestAnimationFrame(() => {
      const nextCursor = before.length + username.length + 2;
      textarea?.focus();
      textarea?.setSelectionRange(nextCursor, nextCursor);
    });
  };

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
      setMentionQuery(null);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="rounded-xl border border-border bg-surface p-5">
      <h3 className="mb-4 text-lg font-semibold text-text">Комментарии</h3>

      <form onSubmit={(event) => void handleSubmit(event)} className="space-y-3">
        <label className="relative block text-sm text-text-muted">
          Текст
          <textarea
            ref={textareaRef}
            value={body}
            onChange={handleBodyChange}
            onKeyUp={(event) => {
              const target = event.target as HTMLTextAreaElement;
              updateMentionState(target.value, target.selectionStart ?? target.value.length);
            }}
            onClick={(event) => {
              const target = event.target as HTMLTextAreaElement;
              updateMentionState(target.value, target.selectionStart ?? target.value.length);
            }}
            rows={3}
            className="mt-1 w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm text-text"
            placeholder="Напишите комментарий или решение... Используйте @username для упоминания"
            aria-label="Текст комментария"
          />
          {mentionQuery != null && mentionSuggestions.length > 0 && (
            <ul className="absolute left-0 z-10 mt-1 w-64 rounded-lg border border-border bg-surface py-1 text-sm shadow-lg">
              {mentionSuggestions.map((member) => (
                <li key={member.id}>
                  <button
                    type="button"
                    onClick={() => applyMention(member.username)}
                    className="block w-full px-3 py-1.5 text-left text-text hover:bg-cream"
                  >
                    @{member.username}
                  </button>
                </li>
              ))}
            </ul>
          )}
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
