/**
 * Web Push subscription helpers (P7 Mobile).
 */

import { request } from "./client";

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  const output = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i += 1) {
    output[i] = raw.charCodeAt(i);
  }
  return output;
}

export async function fetchVapidPublicKey(): Promise<{
  configured: boolean;
  public_key: string;
}> {
  return request("/push/vapid-public-key/");
}

export async function subscribeWebPush(): Promise<{
  ok: boolean;
  reason?: string;
}> {
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
    return { ok: false, reason: "Push не поддерживается в этом браузере." };
  }
  const vapid = await fetchVapidPublicKey();
  if (!vapid.configured || !vapid.public_key) {
    return {
      ok: false,
      reason: "Сервер не настроен (VAPID_PUBLIC_KEY).",
    };
  }
  const permission = await Notification.requestPermission();
  if (permission !== "granted") {
    return { ok: false, reason: "Разрешение на уведомления не выдано." };
  }
  const registration = await navigator.serviceWorker.ready;
  let subscription = await registration.pushManager.getSubscription();
  if (!subscription) {
    subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(
        vapid.public_key,
      ) as BufferSource,
    });
  }
  const json = subscription.toJSON();
  await request("/push/subscribe/", {
    method: "POST",
    body: JSON.stringify({
      endpoint: json.endpoint,
      keys: json.keys,
    }),
  });
  return { ok: true };
}

export async function unsubscribeWebPush(): Promise<void> {
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
    return;
  }
  const registration = await navigator.serviceWorker.ready;
  const subscription = await registration.pushManager.getSubscription();
  if (!subscription) {
    return;
  }
  const endpoint = subscription.endpoint;
  await subscription.unsubscribe();
  try {
    await request("/push/unsubscribe/", {
      method: "POST",
      body: JSON.stringify({ endpoint }),
    });
  } catch {
    // Ignore if already removed server-side.
  }
}
