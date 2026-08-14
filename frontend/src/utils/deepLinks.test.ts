import { describe, expect, it } from "vitest";

import {
  buildDeepLinkSearch,
  mergeDeepLinkSearch,
  parseDeepLinkParams,
} from "./deepLinks";

describe("deepLinks", () => {
  it("parses known query params", () => {
    const params = new URLSearchParams(
      "workspace=2&tab=wbs&node=10&card=5&risk=3&assignee=7&status=4&org_unit=12&obs_role=8&project=9&board=11",
    );
    expect(parseDeepLinkParams(params)).toEqual({
      workspace: 2,
      tab: "wbs",
      node: 10,
      card: 5,
      risk: 3,
      assignee: 7,
      status: 4,
      orgUnit: 12,
      obsRole: 8,
      project: 9,
      board: 11,
    });
  });

  it("returns nulls for missing or invalid ints", () => {
    const params = new URLSearchParams("workspace=abc&tab=risks");
    expect(parseDeepLinkParams(params)).toEqual({
      workspace: null,
      tab: "risks",
      node: null,
      card: null,
      risk: null,
      assignee: null,
      status: null,
      orgUnit: null,
      obsRole: null,
      project: null,
      board: null,
    });
  });

  it("builds search params omitting nulls", () => {
    const built = buildDeepLinkSearch({
      workspace: 1,
      tab: "kanban",
      card: 42,
      board: 3,
      assignee: null,
    });
    expect(built.toString()).toBe("workspace=1&tab=kanban&card=42&board=3");
  });

  it("merges updates and removes keys with null", () => {
    const current = new URLSearchParams("workspace=1&tab=wbs&node=10&assignee=2");
    const merged = mergeDeepLinkSearch(current, {
      tab: "risks",
      node: null,
      risk: 8,
      assignee: 3,
      orgUnit: 4,
      obsRole: null,
    });
    expect(Object.fromEntries(merged.entries())).toEqual({
      workspace: "1",
      tab: "risks",
      risk: "8",
      assignee: "3",
      org_unit: "4",
    });
  });
});
