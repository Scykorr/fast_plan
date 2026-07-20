/** Client-side E2E helpers for DM chats (Web Crypto ECDH P-256 + AES-GCM). */

export type JsonWebKeyLike = JsonWebKey;

const PRIV_KEY = (userId: number) => `fast_plan_e2e_priv_v1_${userId}`;
const ROOM_KEY = (roomId: number) => `fast_plan_e2e_room_v1_${roomId}`;

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

export async function ensureIdentity(userId: number): Promise<{
  publicJwk: JsonWebKey;
  privateKey: CryptoKey;
}> {
  const stored = localStorage.getItem(PRIV_KEY(userId));
  if (stored) {
    const jwk = JSON.parse(stored) as JsonWebKey;
    const privateKey = await importPrivateJwk(jwk);
    const { d: _d, ...publicJwk } = jwk;
    return { publicJwk, privateKey };
  }
  const pair = await crypto.subtle.generateKey(
    { name: "ECDH", namedCurve: "P-256" },
    true,
    ["deriveBits"],
  );
  const privateJwk = await crypto.subtle.exportKey("jwk", pair.privateKey);
  const publicJwk = await crypto.subtle.exportKey("jwk", pair.publicKey);
  localStorage.setItem(PRIV_KEY(userId), JSON.stringify(privateJwk));
  return { publicJwk, privateKey: pair.privateKey };
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

type CryptoApi = {
  putMyPublicKey: (publicJwk: JsonWebKey) => Promise<unknown>;
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
