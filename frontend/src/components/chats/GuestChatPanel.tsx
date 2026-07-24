import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";

import { createChatsApi, type ChatMessage } from "../../api/chats";
import { parseApiError } from "../../api/errors";
import { ErrorMessage } from "../ErrorMessage";

type Props = {
  token: string;
  canPost: boolean;
};

export function GuestChatPanel({ token, canPost }: Props) {
  const api = useMemo(() => createChatsApi(), []);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [label, setLabel] = useState("");
  const [body, setBody] = useState("");
  const [guestName, setGuestName] = useState("Гость");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const payload = await api.getGuestChat(token);
      setMessages(payload.results);
      setLabel(payload.room.label);
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить чат"));
    } finally {
      setLoading(false);
    }
  }, [api, token]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const handleSend = async (event: FormEvent) => {
    event.preventDefault();
    if (!body.trim()) {
      return;
    }
    setSending(true);
    try {
      await api.postGuestMessage(token, {
        body: body.trim(),
        guestName: guestName.trim() || "Гость",
      });
      setBody("");
      await refresh();
    } catch (err) {
      setError(parseApiError(err, "Не удалось отправить"));
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="flex h-full min-h-[22rem] flex-col gap-3 rounded-xl border border-border bg-surface p-3 lg:min-h-[28rem]">
      <div className="border-b border-border pb-2">
        <h2 className="truncate text-base font-semibold text-text">Чат проекта</h2>
        <p className="text-[11px] text-text-muted">
          {label || "Гостевой доступ"}
          {!canPost ? " · только чтение" : ""}
        </p>
      </div>

      {error && <ErrorMessage message={error} onDismiss={() => setError("")} />}

      {loading ? (
        <p className="px-1 py-6 text-center text-xs text-text-muted">Загрузка…</p>
      ) : (
        <div className="flex min-h-0 flex-1 flex-col gap-3 lg:flex-row">
          <div className="min-h-0 flex-1 space-y-2 overflow-y-auto rounded-lg border border-border bg-cream/40 p-2">
            {messages.length === 0 ? (
              <p className="px-1 py-6 text-center text-xs text-text-muted">
                Пока нет сообщений
              </p>
            ) : (
              messages.map((message) => (
                <article
                  key={message.id}
                  className="rounded-lg border border-border/80 bg-surface px-2.5 py-1.5"
                >
                  <div className="mb-0.5 flex items-baseline justify-between gap-2">
                    <span className="truncate text-xs font-medium text-text">
                      {message.author_email}
                    </span>
                    <time className="shrink-0 text-[10px] text-text-muted">
                      {new Date(message.created_at).toLocaleString("ru-RU")}
                    </time>
                  </div>
                  {message.is_deleted ? (
                    <p className="text-sm italic text-text-muted">Удалено</p>
                  ) : (
                    <p className="whitespace-pre-wrap text-sm leading-snug text-text">
                      {message.body}
                    </p>
                  )}
                  {message.reactions.length > 0 && (
                    <div className="mt-1 flex flex-wrap gap-1">
                      {message.reactions.map((reaction) => (
                        <span
                          key={`${reaction.emoji ?? reaction.gif_url}-${reaction.count}`}
                          className="rounded-full border border-border bg-cream px-1.5 py-0.5 text-xs"
                        >
                          {reaction.kind === "gif" ? "GIF" : reaction.emoji}{" "}
                          {reaction.count}
                        </span>
                      ))}
                    </div>
                  )}
                </article>
              ))
            )}
          </div>

          {canPost && (
            <form
              onSubmit={(event) => void handleSend(event)}
              className="flex w-full shrink-0 flex-col gap-2 rounded-lg border border-border bg-cream/30 p-2 lg:w-[min(100%,22rem)]"
            >
              <input
                value={guestName}
                onChange={(event) => setGuestName(event.target.value)}
                placeholder="Ваше имя"
                className="w-full rounded-md border border-border bg-surface px-2.5 py-1.5 text-sm text-text"
              />
              <textarea
                value={body}
                onChange={(event) => setBody(event.target.value)}
                rows={3}
                placeholder="Сообщение…"
                className="w-full resize-y rounded-md border border-border bg-surface px-2.5 py-2 text-sm text-text"
              />
              <button
                type="submit"
                disabled={sending || !body.trim()}
                className="rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-white hover:bg-primary-hover disabled:opacity-50"
              >
                {sending ? "…" : "Отправить"}
              </button>
            </form>
          )}
        </div>
      )}
    </div>
  );
}
