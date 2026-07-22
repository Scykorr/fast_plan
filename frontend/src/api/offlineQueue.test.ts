import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  enqueueOfflineMutation,
  flushOfflineQueue,
  listOfflineQueue,
  mutateOrQueue,
} from "./offlineQueue";

vi.mock("./client", () => ({
  getActiveWorkspaceId: () => 1,
  request: vi.fn(),
}));

import { request } from "./client";

describe("offlineQueue", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.mocked(request).mockReset();
    Object.defineProperty(navigator, "onLine", {
      configurable: true,
      value: true,
    });
  });

  it("enqueues when offline", async () => {
    Object.defineProperty(navigator, "onLine", {
      configurable: true,
      value: false,
    });
    const result = await mutateOrQueue({
      kind: "crm.activity.create",
      path: "/crm/activities/",
      method: "POST",
      body: { subject: "x" },
      label: "Активность: x",
      execute: () => Promise.resolve({ id: 1 }),
    });
    expect(result.queued).toBe(true);
    expect(listOfflineQueue()).toHaveLength(1);
  });

  it("flushes queue when online", async () => {
    enqueueOfflineMutation({
      kind: "crm.activity.create",
      path: "/crm/activities/",
      method: "POST",
      body: { subject: "offline note" },
      label: "note",
    });
    vi.mocked(request).mockResolvedValueOnce({ id: 99 });
    const result = await flushOfflineQueue();
    expect(result.sent).toBe(1);
    expect(result.remaining).toBe(0);
    expect(listOfflineQueue()).toHaveLength(0);
  });
});
