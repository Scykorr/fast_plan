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
    <div className="rounded-2xl border border-border bg-surface p-6 shadow-sm space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-text">Чат проекта</h2>
        <p className="text-sm text-text-muted">{label || "Гостевой доступ"}</p>
      </div>
      {error && <ErrorMessage message={error} onDismiss={() => setError("")} />}
      {loading ? (
        <p className="text-sm text-text-muted">Загрузка…</p>
      ) : (
        <div className="max-h-80 space-y-2 overflow-y-auto rounded-lg border border-border bg-cream/40 p-3">
          {messages.length === 0 ? (
            <p className="text-sm text-text-muted">Пока нет сообщений</p>
          ) : (
            messages.map((message) => (
              <div key={message.id} className="rounded-lg bg-surface px-3 py-2 text-sm border border-border">
                <p className="font-medium text-text">{message.author_email}</p>
                {message.is_deleted ? (
                  <p className="italic text-text-muted">Удалено</p>
                ) : (
                  <p className="whitespace-pre-wrap text-text">{message.body}</p>
                )}
              </div>
            ))
          )}
        </div>
      )}
      {canPost && (
        <form onSubmit={(event) => void handleSend(event)} className="space-y-2">
          <input
            value={guestName}
            onChange={(event) => setGuestName(event.target.value)}
            placeholder="Ваше имя"
            className="w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm"
          />
          <textarea
            value={body}
            onChange={(event) => setBody(event.target.value)}
            rows={3}
            placeholder="Сообщение…"
            className="w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm"
          />
          <button
            type="submit"
            disabled={sending || !body.trim()}
            className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
          >
            Отправить
          </button>
        </form>
      )}
    </div>
  );
}
