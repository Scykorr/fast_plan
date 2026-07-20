/** Client-side E2E helpers for DM chats (Web Crypto ECDH P-256 + AES-GCM). */

import { RECOVERY_WORDS } from "./recoveryWords";

export type JsonWebKeyLike = JsonWebKey;

export type EncryptedPayload = {
  text: string;
  file?: {
    kind: "attachment" | "voice";
    name: string;
    mime: string;
    duration?: number | null;
  };
};

const PRIV_KEY = (userId: number) => `fast_plan_e2e_priv_v1_${userId}`;
const ROOM_KEY = (roomId: number) => `fast_plan_e2e_room_v1_${roomId}`;
const PHRASE_SHOWN = (userId: number) => `fast_plan_e2e_phrase_ack_v1_${userId}`;

function b64encode(buf: ArrayBuffer | Uint8Array): string {
  const bytes = buf instanceof Uint8Array ? buf : new Uint8Array(buf);
  let binary = "";
  bytes.forEach((b) => {
    binary += String.fromCharCode(b);
  });
  return btoa(binary);
}

function b64decode(value: string): Uint8Array<ArrayBuffer> {
  const binary = atob(value);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

async function importPrivateJwk(jwk: JsonWebKey): Promise<CryptoKey> {
  return crypto.subtle.importKey(
    "jwk",
    jwk,
    { name: "ECDH", namedCurve: "P-256" },
    true,
    ["deriveBits"],
  );
}

async function importPublicJwk(jwk: JsonWebKey): Promise<CryptoKey> {
  return crypto.subtle.importKey(
    "jwk",
    { ...jwk, key_ops: ["deriveBits"], ext: true },
    { name: "ECDH", namedCurve: "P-256" },
    true,
    [],
  );
}

function storePrivateJwk(userId: number, privateJwk: JsonWebKey) {
  localStorage.setItem(PRIV_KEY(userId), JSON.stringify(privateJwk));
}

export function hasLocalIdentity(userId: number): boolean {
  return Boolean(localStorage.getItem(PRIV_KEY(userId)));
}

export function hasAcknowledgedRecoveryPhrase(userId: number): boolean {
  return localStorage.getItem(PHRASE_SHOWN(userId)) === "1";
}

export function acknowledgeRecoveryPhrase(userId: number) {
  localStorage.setItem(PHRASE_SHOWN(userId), "1");
}

export async function ensureIdentity(userId: number): Promise<{
  publicJwk: JsonWebKey;
  privateKey: CryptoKey;
  privateJwk: JsonWebKey;
}> {
  const stored = localStorage.getItem(PRIV_KEY(userId));
  if (stored) {
    const jwk = JSON.parse(stored) as JsonWebKey;
    const privateKey = await importPrivateJwk(jwk);
    const { d: _d, ...publicJwk } = jwk;
    return { publicJwk, privateKey, privateJwk: jwk };
  }
  const pair = await crypto.subtle.generateKey(
    { name: "ECDH", namedCurve: "P-256" },
    true,
    ["deriveBits"],
  );
  const privateJwk = await crypto.subtle.exportKey("jwk", pair.privateKey);
  const publicJwk = await crypto.subtle.exportKey("jwk", pair.publicKey);
  storePrivateJwk(userId, privateJwk);
  return { publicJwk, privateKey: pair.privateKey, privateJwk };
}

/** 12-word recovery phrase from 12 random bytes (wordlist size 256). */
export function generateRecoveryPhrase(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(12));
  return Array.from(bytes, (b) => RECOVERY_WORDS[b]).join(" ");
}

export function normalizeRecoveryPhrase(phrase: string): string {
  return phrase
    .trim()
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean)
    .join(" ");
}

export function validateRecoveryPhrase(phrase: string): string[] | null {
  const words = normalizeRecoveryPhrase(phrase).split(" ");
  if (words.length !== 12) {
    return null;
  }
  const allowed = new Set<string>(RECOVERY_WORDS as unknown as string[]);
  if (!words.every((w) => allowed.has(w))) {
    return null;
  }
  return words;
}

async function deriveRecoveryKey(
  phrase: string,
  saltB64: string,
): Promise<CryptoKey> {
  const words = validateRecoveryPhrase(phrase);
  if (!words) {
    throw new Error("Фраза восстановления должна содержать 12 слов из словаря.");
  }
  const material = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(words.join(" ")),
    "PBKDF2",
    false,
    ["deriveKey"],
  );
  return crypto.subtle.deriveKey(
    {
      name: "PBKDF2",
      salt: b64decode(saltB64),
      iterations: 210_000,
      hash: "SHA-256",
    },
    material,
    { name: "AES-GCM", length: 256 },
    false,
    ["encrypt", "decrypt"],
  );
}

export async function createRecoveryBackup(
  userId: number,
  phrase: string,
): Promise<{ recovery_blob: string; recovery_salt: string; publicJwk: JsonWebKey }> {
  const identity = await ensureIdentity(userId);
  const salt = b64encode(crypto.getRandomValues(new Uint8Array(16)));
  const key = await deriveRecoveryKey(phrase, salt);
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const ct = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv },
    key,
    new TextEncoder().encode(JSON.stringify(identity.privateJwk)),
  );
  return {
    recovery_blob: JSON.stringify({ v: 1, iv: b64encode(iv), ct: b64encode(ct) }),
    recovery_salt: salt,
    publicJwk: identity.publicJwk,
  };
}

export async function restoreFromRecoveryBackup(options: {
  userId: number;
  phrase: string;
  recovery_blob: string;
  recovery_salt: string;
}): Promise<JsonWebKey> {
  const key = await deriveRecoveryKey(options.phrase, options.recovery_salt);
  const payload = JSON.parse(options.recovery_blob) as { iv: string; ct: string };
  const raw = await crypto.subtle.decrypt(
    { name: "AES-GCM", iv: b64decode(payload.iv) },
    key,
    b64decode(payload.ct),
  );
  const privateJwk = JSON.parse(new TextDecoder().decode(raw)) as JsonWebKey;
  if (!privateJwk.d || privateJwk.kty !== "EC") {
    throw new Error("Некорректный backup ключа.");
  }
  storePrivateJwk(options.userId, privateJwk);
  acknowledgeRecoveryPhrase(options.userId);
  const { d: _d, ...publicJwk } = privateJwk;
  return publicJwk;
}

async function deriveWrapKey(
  privateKey: CryptoKey,
  peerPublic: CryptoKey,
  roomId: number,
): Promise<CryptoKey> {
  const bits = await crypto.subtle.deriveBits(
    { name: "ECDH", public: peerPublic },
    privateKey,
    256,
  );
  const baseKey = await crypto.subtle.importKey("raw", bits, "HKDF", false, [
    "deriveKey",
  ]);
  const info = new TextEncoder().encode(`fast-plan-dm-room-${roomId}`);
  return crypto.subtle.deriveKey(
    {
      name: "HKDF",
      hash: "SHA-256",
      salt: new Uint8Array(16),
      info,
    },
    baseKey,
    { name: "AES-GCM", length: 256 },
    false,
    ["encrypt", "decrypt"],
  );
}

async function wrapRoomKey(
  roomKey: CryptoKey,
  wrapKey: CryptoKey,
): Promise<string> {
  const raw = await crypto.subtle.exportKey("raw", roomKey);
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const ct = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, wrapKey, raw);
  return JSON.stringify({
    v: 1,
    iv: b64encode(iv),
    ct: b64encode(ct),
  });
}

async function unwrapRoomKey(
  wrapped: string,
  wrapKey: CryptoKey,
): Promise<CryptoKey> {
  const payload = JSON.parse(wrapped) as { iv: string; ct: string };
  const raw = await crypto.subtle.decrypt(
    { name: "AES-GCM", iv: b64decode(payload.iv) },
    wrapKey,
    b64decode(payload.ct),
  );
  return crypto.subtle.importKey("raw", raw, { name: "AES-GCM", length: 256 }, true, [
    "encrypt",
    "decrypt",
  ]);
}

function cacheRoomKey(roomId: number, key: CryptoKey): Promise<void> {
  return crypto.subtle.exportKey("raw", key).then((raw) => {
    localStorage.setItem(ROOM_KEY(roomId), b64encode(raw));
  });
}

async function loadCachedRoomKey(roomId: number): Promise<CryptoKey | null> {
  const raw = localStorage.getItem(ROOM_KEY(roomId));
  if (!raw) {
    return null;
  }
  return crypto.subtle.importKey(
    "raw",
    b64decode(raw),
    { name: "AES-GCM", length: 256 },
    true,
    ["encrypt", "decrypt"],
  );
}

export async function encryptText(roomKey: CryptoKey, plaintext: string): Promise<string> {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const ct = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv },
    roomKey,
    new TextEncoder().encode(plaintext),
  );
  return JSON.stringify({
    v: 1,
    alg: "A256GCM",
    iv: b64encode(iv),
    ct: b64encode(ct),
  });
}

export async function decryptText(roomKey: CryptoKey, ciphertext: string): Promise<string> {
  const payload = JSON.parse(ciphertext) as { iv: string; ct: string };
  const pt = await crypto.subtle.decrypt(
    { name: "AES-GCM", iv: b64decode(payload.iv) },
    roomKey,
    b64decode(payload.ct),
  );
  return new TextDecoder().decode(pt);
}

export async function encryptPayload(
  roomKey: CryptoKey,
  payload: EncryptedPayload,
): Promise<string> {
  return encryptText(roomKey, JSON.stringify(payload));
}

export async function decryptPayload(
  roomKey: CryptoKey,
  ciphertext: string,
): Promise<EncryptedPayload> {
  const raw = await decryptText(roomKey, ciphertext);
  try {
    const parsed = JSON.parse(raw) as EncryptedPayload | string;
    if (typeof parsed === "string") {
      return { text: parsed };
    }
    if (parsed && typeof parsed === "object" && "text" in parsed) {
      return {
        text: String(parsed.text ?? ""),
        file: parsed.file,
      };
    }
  } catch {
    // Legacy plaintext-in-cipher envelopes that were not JSON objects.
  }
  return { text: raw };
}

/** Encrypt file bytes; returns a Blob of (12-byte IV || ciphertext). */
export async function encryptBytes(
  roomKey: CryptoKey,
  data: ArrayBuffer,
): Promise<Blob> {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const ct = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, roomKey, data);
  const out = new Uint8Array(iv.byteLength + ct.byteLength);
  out.set(iv, 0);
  out.set(new Uint8Array(ct), iv.byteLength);
  return new Blob([out], { type: "application/octet-stream" });
}

export async function decryptBytes(
  roomKey: CryptoKey,
  data: ArrayBuffer,
): Promise<ArrayBuffer> {
  const bytes = new Uint8Array(data);
  if (bytes.byteLength < 13) {
    throw new Error("Файл слишком короткий для расшифровки.");
  }
  const iv = bytes.slice(0, 12);
  const ct = bytes.slice(12);
  return crypto.subtle.decrypt({ name: "AES-GCM", iv }, roomKey, ct);
}

type CryptoApi = {
  putMyPublicKey: (
    publicJwk: JsonWebKey,
    recovery?: { recovery_blob: string; recovery_salt: string },
  ) => Promise<unknown>;
  getUserPublicKey: (userId: number) => Promise<{ public_jwk: JsonWebKey | null }>;
  getRoomWraps: (roomId: number) => Promise<{
    wraps: Array<{ user_id: number; wrapped_key: string }>;
  }>;
  putRoomWraps: (
    roomId: number,
    wraps: Array<{ user_id: number; wrapped_key: string }>,
  ) => Promise<unknown>;
};

/**
 * Ensure AES room key for a DM: unwrap existing wrap or bootstrap for both peers.
 */
export async function ensureDmRoomKey(options: {
  userId: number;
  peerId: number;
  roomId: number;
  api: CryptoApi;
}): Promise<CryptoKey> {
  const cached = await loadCachedRoomKey(options.roomId);
  if (cached) {
    return cached;
  }

  const identity = await ensureIdentity(options.userId);
  await options.api.putMyPublicKey(identity.publicJwk);

  const peerPayload = await options.api.getUserPublicKey(options.peerId);
  const peerPublic = peerPayload.public_jwk
    ? await importPublicJwk(peerPayload.public_jwk)
    : null;

  const { wraps } = await options.api.getRoomWraps(options.roomId);
  const mine = wraps.find((item) => item.user_id === options.userId);
  const peerWrap = wraps.find((item) => item.user_id === options.peerId);

  if (mine && peerPublic) {
    const wrapKey = await deriveWrapKey(
      identity.privateKey,
      peerPublic,
      options.roomId,
    );
    const roomKey = await unwrapRoomKey(mine.wrapped_key, wrapKey);
    await cacheRoomKey(options.roomId, roomKey);
    if (!peerWrap) {
      const forPeer = await wrapRoomKey(roomKey, wrapKey);
      await options.api.putRoomWraps(options.roomId, [
        { user_id: options.peerId, wrapped_key: forPeer },
      ]);
    }
    return roomKey;
  }

  if (mine && !peerPublic) {
    throw new Error(
      "Собеседник ещё не опубликовал ключ. Попросите открыть этот DM.",
    );
  }

  if (!peerPublic) {
    throw new Error(
      "E2E: дождитесь, пока собеседник откроет DM (нужен его публичный ключ).",
    );
  }

  const wrapKey = await deriveWrapKey(
    identity.privateKey,
    peerPublic,
    options.roomId,
  );
  const roomKey = await crypto.subtle.generateKey(
    { name: "AES-GCM", length: 256 },
    true,
    ["encrypt", "decrypt"],
  );
  const wrapped = await wrapRoomKey(roomKey, wrapKey);
  await options.api.putRoomWraps(options.roomId, [
    { user_id: options.userId, wrapped_key: wrapped },
    { user_id: options.peerId, wrapped_key: wrapped },
  ]);
  await cacheRoomKey(options.roomId, roomKey);
  return roomKey;
}
