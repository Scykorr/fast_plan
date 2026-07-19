import { describe, expect, it, vi, beforeEach } from "vitest";

import { getActiveWorkspaceId, request, setActiveWorkspaceId } from "../api/client";

describe("API client workspace header", () => {
  beforeEach(() => {
    setActiveWorkspaceId(null);
    document.cookie = "csrftoken=test-csrf";
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ ok: true }),
      }),
    );
  });

  it("sends X-Workspace-Id and credentials without Bearer token", async () => {
    setActiveWorkspaceId(42);
    expect(getActiveWorkspaceId()).toBe(42);

    await request("/boards/", {});

    expect(fetch).toHaveBeenCalledWith(
      "/api/boards/",
      expect.objectContaining({
        credentials: "include",
        headers: expect.objectContaining({
          "X-Workspace-Id": "42",
        }),
      }),
    );
    const [, init] = vi.mocked(fetch).mock.calls[0];
    expect((init?.headers as Record<string, string>).Authorization).toBeUndefined();
  });

  it("sends CSRF token on mutating requests", async () => {
    await request("/boards/", { method: "POST", body: "{}" });
    expect(fetch).toHaveBeenCalledWith(
      "/api/boards/",
      expect.objectContaining({
        credentials: "include",
        headers: expect.objectContaining({
          "X-CSRFToken": "test-csrf",
        }),
      }),
    );
  });
});
