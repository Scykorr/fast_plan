import { describe, expect, it, vi, beforeEach } from "vitest";

import { getActiveWorkspaceId, request, setActiveWorkspaceId } from "../api/client";

describe("API client workspace header", () => {
  beforeEach(() => {
    setActiveWorkspaceId(null);
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ ok: true }),
      }),
    );
  });

  it("sends X-Workspace-Id when active workspace is set", async () => {
    setActiveWorkspaceId(42);
    expect(getActiveWorkspaceId()).toBe(42);

    await request("/boards/", {}, "token");

    expect(fetch).toHaveBeenCalledWith(
      "/api/boards/",
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer token",
          "X-Workspace-Id": "42",
        }),
      }),
    );
  });
});
