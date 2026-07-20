import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";

import { parseApiError } from "../../api/errors";
import type {
  ChatMessage,
  ChatRoom,
  ChatRoomListItem,
  ChatStatus,
} from "../../api/chats";
import { ErrorMessage } from "../ErrorMessage";
import { useAuth } from "../../context/AuthContext";
import { useChatsApi } from "../../hooks/useChatsApi";
import { useWorkspaceEvents } from "../../hooks/useWorkspaceEvents";
import { useWorkspace } from "../../context/WorkspaceContext";
import { useProjectsApi } from "../../hooks/useProjectsApi";
import { useWorkspaceApi } from "../../hooks/useWorkspaceApi";
import {
  decryptText,
  encryptText,
  ensureDmRoomKey,
  ensureIdentity,
} from "../../lib/chatE2E";
import { ReactionPicker, type ReactionPick } from "./ReactionPicker";

type Props = {
  scope: "project" | "workspace" | "dm";
  projectId?: number;
  roomId?: number;
};

const STATUS_LABELS: Record<ChatStatus, string> = {
  open: "Открыт",
  disabled: "Выключен",
  announcements: "Только оповещения",
  archived: "Архив",
};

export function ChatPanel({ scope, projectId, roomId }: Props) {
  const chatsApi = useChatsApi();
  const projectsApi = useProjectsApi();
  const workspaceApi = useWorkspaceApi();
  const { isAuthenticated, user } = useAuth();
  const { activeWorkspace } = useWorkspace();

  const [room, setRoom] = useState<ChatRoom | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [displayBodies, setDisplayBodies] = useState<Record<number, string>>({});
  const [roomKey, setRoomKey] = useState<CryptoKey | null>(null);
  const [e2eStatus, setE2eStatus] = useState("");
  const [pickerFor, setPickerFor] = useState<number | null>(null);
  const [body, setBody] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [voice, setVoice] = useState<File | null>(null);
  const [replyTo, setReplyTo] = useState<ChatMessage | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [forwardTargets, setForwardTargets] = useState<ChatRoomListItem[]>([]);
  const [forwardMessageId, setForwardMessageId] = useState<number | null>(null);
  const [muteUserId, setMuteUserId] = useState<number | "">("");
  const [dmUserId, setDmUserId] = useState<number | "">("");
  const [participantOptions, setParticipantOptions] = useState<
    Array<{ user_id: number; email: string }>
  >([]);
  const [recording, setRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const loadRoom = useCallback(async () => {
    if (!chatsApi) {
      return null;
    }
    if (roomId) {
      return chatsApi.getRoom(roomId);
    }
    if (scope === "project") {
      if (!projectId) {
        return null;
      }
      return chatsApi.resolveProjectChat(projectId);
    }
    if (scope === "dm") {
      return null;
    }
    return chatsApi.resolveWorkspaceChat();
  }, [chatsApi, scope, projectId, roomId]);

  const refresh = useCallback(async () => {
    if (!chatsApi) {
      return;
    }
    setLoading(true);
    setError("");
    try {
      const nextRoom = await loadRoom();
      if (!nextRoom) {
        setRoom(null);
        setMessages([]);
        setRoomKey(null);
        return;
      }
      setRoom(nextRoom);
      const listed = await chatsApi.listMessages(nextRoom.id);
      setMessages(listed.results);

      if (nextRoom.e2e_enabled && nextRoom.dm_peer_id && user?.id) {
        try {
          const identity = await ensureIdentity(user.id);
          await chatsApi.putMyPublicKey(identity.publicJwk);
          const key = await ensureDmRoomKey({
            userId: user.id,
            peerId: nextRoom.dm_peer_id,
            roomId: nextRoom.id,
            api: chatsApi,
          });
          setRoomKey(key);
          setE2eStatus("E2E включён — текст шифруется на устройстве");
        } catch (err) {
          setRoomKey(null);
          setE2eStatus(
            err instanceof Error ? err.message : "E2E ключ пока недоступен",
          );
        }
      } else {
        setRoomKey(null);
        setE2eStatus("");
      }
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить чат"));
    } finally {
      setLoading(false);
    }
  }, [chatsApi, loadRoom, user?.id]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      const next: Record<number, string> = {};
      for (const message of messages) {
        if (!message.is_encrypted) {
          next[message.id] = message.body;
          continue;
        }
        if (!roomKey) {
          next[message.id] = "🔒 Зашифрованное сообщение";
          continue;
        }
        try {
          next[message.id] = await decryptText(roomKey, message.body);
        } catch {
          next[message.id] = "🔒 Не удалось расшифровать";
        }
      }
      if (!cancelled) {
        setDisplayBodies(next);
      }
    };
    void run();
    return () => {
      cancelled = true;
    };
  }, [messages, roomKey]);

  useWorkspaceEvents(isAuthenticated && Boolean(activeWorkspace), (type, payload) => {
    if (type !== "chat.message" || !room) {
      return;
    }
    if (Number(payload.room_id) === room.id) {
      void refresh();
    }
  });

  useEffect(() => {
    if (scope === "project" && projectId && projectsApi) {
      void projectsApi
        .getProjectMembers(projectId)
        .then((items) =>
          setParticipantOptions(
            items.map((item) => ({ user_id: item.user_id, email: item.email })),
          ),
        )
        .catch(() => undefined);
      return;
    }
    if (workspaceApi) {
      void workspaceApi
        .getMembers()
        .then((items) =>
          setParticipantOptions(
            items.map((item) => ({ user_id: item.user_id, email: item.email })),
          ),
        )
        .catch(() => undefined);
    }
  }, [scope, projectId, projectsApi, workspaceApi]);

  const handleSend = async (event: FormEvent) => {
    event.preventDefault();
    if (!chatsApi || !room || (!body.trim() && !file && !voice)) {
      return;
    }
    setSending(true);
    setError("");
    try {
      const useE2E = Boolean(room.e2e_enabled && body.trim() && !file && !voice);
      if (useE2E && !roomKey) {
        throw new Error(e2eStatus || "E2E ключ недоступен");
      }
      let payloadBody = body.trim();
      if (useE2E && roomKey) {
        payloadBody = await encryptText(roomKey, payloadBody);
      }
      if (editingId) {
        await chatsApi.editMessage(room.id, editingId, payloadBody, useE2E);
        setEditingId(null);
      } else {
        await chatsApi.postMessage(room.id, {
          body: payloadBody,
          replyTo: replyTo?.id ?? null,
          file,
          voice,
          isEncrypted: useE2E,
        });
      }
      setBody("");
      setFile(null);
      setVoice(null);
      setReplyTo(null);
      await refresh();
    } catch (err) {
      setError(
        err instanceof Error && !("response" in err)
          ? err.message
          : parseApiError(err, "Не удалось отправить сообщение"),
      );
    } finally {
      setSending(false);
    }
  };

  const handleReaction = async (messageId: number, reaction: ReactionPick) => {
    if (!chatsApi || !room) {
      return;
    }
    try {
      await chatsApi.toggleReaction(room.id, messageId, reaction);
      setPickerFor(null);
      await refresh();
    } catch (err) {
      setError(parseApiError(err, "Не удалось поставить реакцию"));
    }
  };

  const handleStatus = async (status: ChatStatus) => {
    if (!chatsApi || !room) {
      return;
    }
    try {
      setRoom(await chatsApi.patchStatus(room.id, status));
      await refresh();
    } catch (err) {
      setError(parseApiError(err, "Не удалось изменить режим чата"));
    }
  };

  const openForward = async (messageId: number) => {
    if (!chatsApi || !room) {
      return;
    }
    try {
      const mine = await chatsApi.getMine();
      setForwardTargets(mine.filter((item) => item.id !== room.id));
      setForwardMessageId(messageId);
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить список чатов"));
    }
  };

  const confirmForward = async (targetId: number) => {
    if (!chatsApi || !room || forwardMessageId == null) {
      return;
    }
    try {
      await chatsApi.forwardMessage(room.id, forwardMessageId, targetId);
      setForwardMessageId(null);
      setForwardTargets([]);
    } catch (err) {
      setError(parseApiError(err, "Не удалось переслать сообщение"));
    }
  };

  const handleMute = async () => {
    if (!chatsApi || !room || muteUserId === "") {
      return;
    }
    try {
      await chatsApi.addMute(room.id, { user_id: Number(muteUserId) });
      setMuteUserId("");
      await refresh();
    } catch (err) {
      setError(parseApiError(err, "Не удалось запретить писать"));
    }
  };

  const handleUnmute = async (userId: number) => {
    if (!chatsApi || !room) {
      return;
    }
    try {
      await chatsApi.removeMute(room.id, userId);
      await refresh();
    } catch (err) {
      setError(parseApiError(err, "Не удалось снять запрет"));
    }
  };

  const handleOpenDm = async () => {
    if (!chatsApi || dmUserId === "") {
      return;
    }
    try {
      const dmRoom = await chatsApi.openDm(Number(dmUserId));
      setDmUserId("");
      // Force scope via roomId path: set room then reload through same E2E path
      setRoom(dmRoom);
      const listed = await chatsApi.listMessages(dmRoom.id);
      setMessages(listed.results);
      if (dmRoom.dm_peer_id && user?.id) {
        try {
          const identity = await ensureIdentity(user.id);
          await chatsApi.putMyPublicKey(identity.publicJwk);
          const key = await ensureDmRoomKey({
            userId: user.id,
            peerId: dmRoom.dm_peer_id,
            roomId: dmRoom.id,
            api: chatsApi,
          });
          setRoomKey(key);
          setE2eStatus("E2E включён — текст шифруется на устройстве");
        } catch (err) {
          setRoomKey(null);
          setE2eStatus(
            err instanceof Error ? err.message : "E2E ключ пока недоступен",
          );
        }
      }
    } catch (err) {
      setError(parseApiError(err, "Не удалось открыть DM"));
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        setVoice(new File([blob], `voice-${Date.now()}.webm`, { type: "audio/webm" }));
        stream.getTracks().forEach((track) => track.stop());
      };
      mediaRecorderRef.current = recorder;
      recorder.start();
      setRecording(true);
    } catch {
      setError("Не удалось получить доступ к микрофону");
    }
  };

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    setRecording(false);
  };

  if (loading && !room) {
    return <p className="text-sm text-text-muted">Загрузка чата...</p>;
  }

  if (!room) {
    return (
      <div className="space-y-3 rounded-xl border border-border bg-surface p-4">
        <p className="text-sm text-text-muted">Чат недоступен</p>
        {scope === "workspace" && (
          <div className="flex flex-wrap gap-2">
            <select
              value={dmUserId}
              onChange={(event) =>
                setDmUserId(event.target.value ? Number(event.target.value) : "")
              }
              className="rounded-lg border border-border bg-cream px-2 py-1.5 text-sm"
            >
              <option value="">Открыть DM с…</option>
              {participantOptions
                .filter((item) => item.user_id !== user?.id)
                .map((item) => (
                  <option key={item.user_id} value={item.user_id}>
                    {item.email}
                  </option>
                ))}
            </select>
            <button
              type="button"
              onClick={() => void handleOpenDm()}
              className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white"
            >
              DM
            </button>
          </div>
        )}
        {error && <ErrorMessage message={error} onDismiss={() => setError("")} />}
      </div>
    );
  }

  const banner =
    room.is_archived || room.status === "archived"
      ? "Чат в архиве (только чтение)."
      : room.status === "disabled"
        ? "Чат отключён руководителем. История сохранена."
        : room.status === "announcements"
          ? "Режим оповещений: писать могут только руководители."
          : room.is_muted
            ? "Вам запрещено писать в этот чат."
            : null;

  return (
    <div className="space-y-4 rounded-xl border border-border bg-surface p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-text">
            {room.scope === "dm" && room.dm_peer_email
              ? `DM: ${room.dm_peer_email}`
              : room.label}
          </h2>
          <p className="text-xs text-text-muted">
            Режим: {STATUS_LABELS[room.status]}
            {room.e2e_enabled ? " · E2E DM" : ""}
          </p>
          {e2eStatus && (
            <p className="mt-1 text-xs text-primary">{e2eStatus}</p>
          )}
        </div>
        {room.is_moderator && room.scope !== "dm" && (
          <div className="flex flex-wrap gap-2">
            {(["open", "announcements", "disabled", "archived"] as const).map(
              (value) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => void handleStatus(value)}
                  className={[
                    "rounded-lg border px-3 py-1.5 text-xs font-medium",
                    room.status === value
                      ? "border-primary bg-primary text-white"
                      : "border-border bg-cream text-text hover:border-primary",
                  ].join(" ")}
                >
                  {STATUS_LABELS[value]}
                </button>
              ),
            )}
          </div>
        )}
      </div>

      {scope === "workspace" && (
        <div className="flex flex-wrap gap-2 border-b border-border pb-3">
          <select
            value={dmUserId}
            onChange={(event) =>
              setDmUserId(event.target.value ? Number(event.target.value) : "")
            }
            className="rounded-lg border border-border bg-cream px-2 py-1.5 text-sm"
          >
            <option value="">Личный чат с…</option>
            {participantOptions
              .filter((item) => item.user_id !== user?.id)
              .map((item) => (
                <option key={item.user_id} value={item.user_id}>
                  {item.email}
                </option>
              ))}
          </select>
          <button
            type="button"
            onClick={() => void handleOpenDm()}
            className="rounded-lg border border-border bg-cream px-3 py-1.5 text-sm font-medium hover:border-primary"
          >
            Открыть DM
          </button>
        </div>
      )}

      {error && <ErrorMessage message={error} onDismiss={() => setError("")} />}
      {banner && (
        <p className="rounded-lg border border-border bg-cream px-3 py-2 text-sm text-text">
          {banner}
        </p>
      )}

      {room.is_moderator && room.scope !== "dm" && (
        <div className="space-y-2 rounded-lg border border-border bg-cream/60 p-3">
          <p className="text-sm font-medium text-text">Запретить писать</p>
          <div className="flex flex-wrap gap-2">
            <select
              value={muteUserId}
              onChange={(event) =>
                setMuteUserId(event.target.value ? Number(event.target.value) : "")
              }
              className="rounded-lg border border-border bg-surface px-2 py-1.5 text-sm"
            >
              <option value="">Участник…</option>
              {participantOptions
                .filter((item) => item.user_id !== user?.id)
                .filter(
                  (item) => !room.mutes.some((mute) => mute.user_id === item.user_id),
                )
                .map((item) => (
                  <option key={item.user_id} value={item.user_id}>
                    {item.email}
                  </option>
                ))}
            </select>
            <button
              type="button"
              onClick={() => void handleMute()}
              className="rounded-lg border border-border bg-surface px-3 py-1.5 text-sm font-medium text-text hover:border-primary"
            >
              Запретить
            </button>
          </div>
          {room.mutes.length > 0 && (
            <ul className="space-y-1 text-sm">
              {room.mutes.map((mute) => (
                <li
                  key={mute.id}
                  className="flex items-center justify-between gap-2 rounded-md bg-surface px-2 py-1"
                >
                  <span>
                    {mute.user_email}
                    {mute.reason ? ` — ${mute.reason}` : ""}
                  </span>
                  <button
                    type="button"
                    onClick={() => void handleUnmute(mute.user_id)}
                    className="text-xs text-primary hover:underline"
                  >
                    Снять
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <div className="max-h-96 space-y-3 overflow-y-auto rounded-lg border border-border bg-cream/40 p-3">
        {messages.length === 0 ? (
          <p className="text-sm text-text-muted">Пока нет сообщений</p>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className="rounded-lg border border-border bg-surface px-3 py-2 text-sm"
            >
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <span className="font-medium text-text">{message.author_email}</span>
                <time className="text-xs text-text-muted">
                  {new Date(message.created_at).toLocaleString("ru-RU")}
                  {message.edited_at ? " · изменено" : ""}
                </time>
              </div>
              {message.reply_to_preview && (
                <p className="mt-1 rounded border-l-2 border-primary/50 bg-cream px-2 py-1 text-xs text-text-muted">
                  ↪ {message.reply_to_preview.author_email}:{" "}
                  {message.reply_to_preview.body}
                </p>
              )}
              {message.forward_source_label && (
                <p className="mt-1 text-xs text-text-muted">
                  Переслано из {message.forward_source_label}
                </p>
              )}
              {message.is_deleted ? (
                <p className="mt-1 italic text-text-muted">Сообщение удалено</p>
              ) : (
                <>
                  {message.body && (
                    <p className="mt-1 whitespace-pre-wrap text-text">
                      {displayBodies[message.id] ?? message.body}
                      {message.is_encrypted && (
                        <span className="ml-2 text-[10px] uppercase tracking-wide text-primary">
                          e2e
                        </span>
                      )}
                    </p>
                  )}
                  {message.attachment_url && (
                    <a
                      href={message.attachment_url}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-1 inline-block text-xs text-primary hover:underline"
                    >
                      Вложение
                    </a>
                  )}
                  {message.voice_url && (
                    <audio controls className="mt-2 w-full" src={message.voice_url}>
                      <track kind="captions" />
                    </audio>
                  )}
                </>
              )}
              {!message.is_deleted && (
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  {message.reactions.map((reaction) => (
                    <button
                      key={`${reaction.kind}:${reaction.emoji ?? reaction.gif_url}`}
                      type="button"
                      onClick={() =>
                        void handleReaction(
                          message.id,
                          reaction.kind === "gif" && reaction.gif_url
                            ? { kind: "gif", gif_url: reaction.gif_url }
                            : { kind: "emoji", emoji: reaction.emoji || "👍" },
                        )
                      }
                      className="inline-flex items-center gap-1 rounded-full border border-border bg-cream px-2 py-0.5 text-xs"
                    >
                      {reaction.kind === "gif" && reaction.gif_url ? (
                        <img
                          src={reaction.gif_url}
                          alt=""
                          className="h-5 w-5 rounded object-cover"
                        />
                      ) : (
                        <span>{reaction.emoji}</span>
                      )}
                      <span>{reaction.count}</span>
                    </button>
                  ))}
                  <div className="relative">
                    <button
                      type="button"
                      onClick={() =>
                        setPickerFor((prev) =>
                          prev === message.id ? null : message.id,
                        )
                      }
                      className="text-xs opacity-70 hover:opacity-100"
                      title="Реакция"
                    >
                      +😊
                    </button>
                    {pickerFor === message.id && (
                      <ReactionPicker
                        onPick={(pick) => void handleReaction(message.id, pick)}
                        onClose={() => setPickerFor(null)}
                      />
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() => setReplyTo(message)}
                    className="text-xs text-primary hover:underline"
                  >
                    Ответить
                  </button>
                  {!message.is_encrypted && (
                    <button
                      type="button"
                      onClick={() => void openForward(message.id)}
                      className="text-xs text-primary hover:underline"
                    >
                      Переслать
                    </button>
                  )}
                  {(message.author_id === user?.id || room.is_moderator) && (
                    <>
                      <button
                        type="button"
                        onClick={() => {
                          setEditingId(message.id);
                          setBody(displayBodies[message.id] ?? message.body);
                          setReplyTo(null);
                        }}
                        className="text-xs text-text-muted hover:text-primary"
                      >
                        Изменить
                      </button>
                      <button
                        type="button"
                        onClick={() =>
                          void chatsApi
                            ?.deleteMessage(room.id, message.id)
                            .then(() => refresh())
                        }
                        className="text-xs text-text-muted hover:text-primary"
                      >
                        Удалить
                      </button>
                    </>
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {room.can_post ? (
        <form onSubmit={(event) => void handleSend(event)} className="space-y-2">
          {replyTo && (
            <p className="text-xs text-text-muted">
              Ответ на: {replyTo.author_email} — {replyTo.body.slice(0, 80)}{" "}
              <button type="button" className="text-primary" onClick={() => setReplyTo(null)}>
                отмена
              </button>
            </p>
          )}
          {editingId && (
            <p className="text-xs text-text-muted">
              Редактирование #{editingId}{" "}
              <button
                type="button"
                className="text-primary"
                onClick={() => {
                  setEditingId(null);
                  setBody("");
                }}
              >
                отмена
              </button>
            </p>
          )}
          <textarea
            value={body}
            onChange={(event) => setBody(event.target.value)}
            rows={3}
            placeholder={
              room.e2e_enabled
                ? "Сообщение (шифруется на устройстве)…"
                : "Сообщение…"
            }
            className="w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
          />
          <div className="flex flex-wrap items-center gap-2">
            {!room.e2e_enabled && (
              <input
                type="file"
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                className="text-xs text-text-muted"
              />
            )}
            {!editingId && !room.e2e_enabled && (
              <button
                type="button"
                onClick={() => (recording ? stopRecording() : void startRecording())}
                className="rounded-lg border border-border bg-cream px-3 py-1.5 text-xs font-medium"
              >
                {recording ? "Стоп запись" : "Голосовое"}
              </button>
            )}
            {voice && (
              <span className="text-xs text-text-muted">Голос: {voice.name}</span>
            )}
            <button
              type="submit"
              disabled={
                sending ||
                (!body.trim() && !file && !voice && !editingId) ||
                (Boolean(room.e2e_enabled && body.trim()) && !roomKey)
              }
              className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary-hover disabled:opacity-60"
            >
              {sending ? "…" : editingId ? "Сохранить" : "Отправить"}
            </button>
          </div>
        </form>
      ) : (
        <p className="text-sm text-text-muted">Отправка сообщений недоступна.</p>
      )}

      {forwardMessageId != null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-xl border border-border bg-surface p-5 shadow-lg">
            <h3 className="text-lg font-semibold text-text">Переслать в чат</h3>
            <ul className="mt-3 max-h-64 space-y-1 overflow-y-auto">
              {forwardTargets.length === 0 ? (
                <li className="text-sm text-text-muted">Нет других доступных чатов</li>
              ) : (
                forwardTargets.map((target) => (
                  <li key={target.id}>
                    <button
                      type="button"
                      onClick={() => void confirmForward(target.id)}
                      className="w-full rounded-lg px-3 py-2 text-left text-sm hover:bg-cream"
                    >
                      {target.label}
                      <span className="ml-2 text-xs text-text-muted">
                        ({STATUS_LABELS[target.status]})
                      </span>
                    </button>
                  </li>
                ))
              )}
            </ul>
            <button
              type="button"
              onClick={() => {
                setForwardMessageId(null);
                setForwardTargets([]);
              }}
              className="mt-4 rounded-lg border border-border px-3 py-1.5 text-sm text-text-muted hover:bg-cream"
            >
              Отмена
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
