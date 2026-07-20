import { request, requestForm } from "./client";

export type ChatStatus = "open" | "disabled" | "announcements" | "archived";

export type ChatMute = {
  id: number;
  user_id: number;
  user_email: string;
  reason: string;
  created_at: string;
  muted_by: number | null;
};

export type ChatReactionGroup = {
  kind: "emoji" | "gif";
  emoji: string | null;
  gif_url: string | null;
  count: number;
  user_ids: number[];
};

export type ChatRoom = {
  id: number;
  scope: "project" | "workspace" | "dm";
  status: ChatStatus;
  label: string;
  project_id: number | null;
  workspace_id: number | null;
  dm_peer_email: string | null;
  dm_peer_id: number | null;
  can_post: boolean;
  is_moderator: boolean;
  is_muted: boolean;
  is_archived: boolean;
  e2e_enabled: boolean;
  mutes: ChatMute[];
  status_changed_at: string | null;
  archived_at: string | null;
  created_at: string;
};

export type ChatRoomListItem = {
  id: number;
  scope: "project" | "workspace" | "dm";
  status: ChatStatus;
  label: string;
  project_id: number | null;
  workspace_id: number | null;
  dm_peer_email: string | null;
  archived_at: string | null;
};

export type ChatMessage = {
  id: number;
  room: number;
  author_id: number | null;
  author_email: string;
  guest_name: string;
  body: string;
  is_encrypted: boolean;
  reply_to: number | null;
  reply_to_preview: {
    id: number;
    body: string;
    author_email: string;
    is_encrypted?: boolean;
  } | null;
  forwarded_from: number | null;
  forward_source_label: string;
  attachment_url: string | null;
  voice_url: string | null;
  voice_duration_seconds: number | null;
  reactions: ChatReactionGroup[];
  edited_at: string | null;
  deleted_at: string | null;
  is_deleted: boolean;
  created_at: string;
};

export type GuestChatPayload = {
  room: {
    id: number;
    status: ChatStatus;
    label: string;
    can_post: boolean;
    chat_can_post: boolean;
  };
  results: ChatMessage[];
};

export type ReactionPayload =
  | { kind?: "emoji"; emoji: string }
  | { kind: "gif"; gif_url: string };

async function postMessageForm(
  path: string,
  options: {
    body?: string;
    replyTo?: number | null;
    file?: File | null;
    voice?: File | null;
    voiceDuration?: number | null;
    guestName?: string;
    isEncrypted?: boolean;
  },
) {
  const form = new FormData();
  if (options.body) {
    form.append("body", options.body);
  }
  if (options.replyTo) {
    form.append("reply_to", String(options.replyTo));
  }
  if (options.guestName) {
    form.append("guest_name", options.guestName);
  }
  if (options.voiceDuration) {
    form.append("voice_duration_seconds", String(options.voiceDuration));
  }
  if (options.isEncrypted) {
    form.append("is_encrypted", "true");
  }
  if (options.file) {
    form.append("attachment", options.file);
  }
  if (options.voice) {
    form.append("voice", options.voice);
  }
  return requestForm<ChatMessage>(path, form, "POST");
}

export function createChatsApi() {
  return {
    resolveProjectChat: (projectId: number) =>
      request<ChatRoom>(`/chats/?scope=project&project_id=${projectId}`, {}),

    resolveWorkspaceChat: () =>
      request<ChatRoom>("/chats/?scope=workspace", {}),

    openDm: (userId: number) =>
      request<ChatRoom>("/chats/dm/", {
        method: "POST",
        body: JSON.stringify({ user_id: userId }),
      }),

    getMine: (includeArchived = false) =>
      request<ChatRoomListItem[]>(
        `/chats/mine/${includeArchived ? "?include_archived=1" : ""}`,
        {},
      ),

    getRoom: (roomId: number) => request<ChatRoom>(`/chats/${roomId}/`, {}),

    patchStatus: (roomId: number, status: ChatStatus) =>
      request<ChatRoom>(`/chats/${roomId}/`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      }),

    listMutes: (roomId: number) =>
      request<ChatMute[]>(`/chats/${roomId}/mutes/`, {}),

    addMute: (roomId: number, body: { user_id: number; reason?: string }) =>
      request<ChatMute>(`/chats/${roomId}/mutes/`, {
        method: "POST",
        body: JSON.stringify(body),
      }),

    removeMute: (roomId: number, userId: number) =>
      request<void>(`/chats/${roomId}/mutes/${userId}/`, { method: "DELETE" }),

    listMessages: (roomId: number) =>
      request<{ results: ChatMessage[]; status: ChatStatus }>(
        `/chats/${roomId}/messages/`,
        {},
      ),

    postMessage: (
      roomId: number,
      options: {
        body?: string;
        replyTo?: number | null;
        file?: File | null;
        voice?: File | null;
        voiceDuration?: number | null;
        isEncrypted?: boolean;
      },
    ) => {
      if (options.file || options.voice) {
        return postMessageForm(`/chats/${roomId}/messages/`, options);
      }
      return request<ChatMessage>(`/chats/${roomId}/messages/`, {
        method: "POST",
        body: JSON.stringify({
          body: options.body ?? "",
          reply_to: options.replyTo ?? null,
          is_encrypted: Boolean(options.isEncrypted),
        }),
      });
    },

    editMessage: (
      roomId: number,
      messageId: number,
      body: string,
      isEncrypted = false,
    ) =>
      request<ChatMessage>(`/chats/${roomId}/messages/${messageId}/`, {
        method: "PATCH",
        body: JSON.stringify({ body, is_encrypted: isEncrypted }),
      }),

    deleteMessage: (roomId: number, messageId: number) =>
      request<void>(`/chats/${roomId}/messages/${messageId}/`, {
        method: "DELETE",
      }),

    forwardMessage: (roomId: number, messageId: number, targetChatId: number) =>
      request<ChatMessage>(`/chats/${roomId}/messages/${messageId}/forward/`, {
        method: "POST",
        body: JSON.stringify({ target_chat_id: targetChatId }),
      }),

    toggleReaction: (roomId: number, messageId: number, reaction: ReactionPayload) =>
      request<{ toggled: string; message: ChatMessage }>(
        `/chats/${roomId}/messages/${messageId}/reactions/`,
        {
          method: "POST",
          body: JSON.stringify(
            reaction.kind === "gif"
              ? { kind: "gif", gif_url: reaction.gif_url }
              : { kind: "emoji", emoji: reaction.emoji },
          ),
        },
      ),

    putMyPublicKey: (
      publicJwk: JsonWebKey,
      recovery?: { recovery_blob: string; recovery_salt: string; clear_recovery?: boolean },
    ) =>
      request<{
        user_id: number;
        public_jwk: JsonWebKey;
        has_recovery: boolean;
        recovery_blob: string;
        recovery_salt: string;
      }>("/chats/crypto/me/", {
        method: "PUT",
        body: JSON.stringify({
          public_jwk: publicJwk,
          ...(recovery ?? {}),
        }),
      }),

    getMyCryptoKey: () =>
      request<{
        user_id: number;
        public_jwk: JsonWebKey | null;
        has_recovery: boolean;
        recovery_blob: string;
        recovery_salt: string;
      }>("/chats/crypto/me/", {}),

    getUserPublicKey: (userId: number) =>
      request<{ user_id: number; public_jwk: JsonWebKey | null }>(
        `/chats/crypto/users/${userId}/`,
        {},
      ),

    getRoomWraps: (roomId: number) =>
      request<{
        room_id: number;
        wraps: Array<{ user_id: number; wrapped_key: string; updated_at: string }>;
      }>(`/chats/${roomId}/e2e/`, {}),

    putRoomWraps: (
      roomId: number,
      wraps: Array<{ user_id: number; wrapped_key: string }>,
    ) =>
      request<{
        room_id: number;
        wraps: Array<{ user_id: number; wrapped_key: string }>;
      }>(`/chats/${roomId}/e2e/`, {
        method: "PUT",
        body: JSON.stringify({ wraps }),
      }),

    getGuestChat: (token: string) =>
      request<GuestChatPayload>(`/share/${token}/chat/`, {}),

    postGuestMessage: (
      token: string,
      options: {
        body?: string;
        guestName?: string;
        replyTo?: number | null;
        file?: File | null;
        voice?: File | null;
      },
    ) => {
      if (options.file || options.voice) {
        return postMessageForm(`/share/${token}/chat/`, options);
      }
      return request<ChatMessage>(`/share/${token}/chat/`, {
        method: "POST",
        body: JSON.stringify({
          body: options.body ?? "",
          guest_name: options.guestName ?? "Гость",
          reply_to: options.replyTo ?? null,
        }),
      });
    },
  };
}

export type ChatsApi = ReturnType<typeof createChatsApi>;
