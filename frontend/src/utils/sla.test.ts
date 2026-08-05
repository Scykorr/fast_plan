import { describe, expect, it } from "vitest";

import { getSlaInfo, slaBadgeClass } from "./sla";

describe("sla", () => {
  const now = new Date("2026-08-05T12:00:00Z");

  it("returns none without due_at", () => {
    expect(getSlaInfo(null, now).state).toBe("none");
  });

  it("marks overdue", () => {
    const info = getSlaInfo("2026-08-05T10:00:00Z", now);
    expect(info.state).toBe("overdue");
    expect(info.label).toMatch(/просрочено/);
  });

  it("marks soon within 4h", () => {
    const info = getSlaInfo("2026-08-05T14:00:00Z", now);
    expect(info.state).toBe("soon");
  });

  it("marks ok when far enough", () => {
    const info = getSlaInfo("2026-08-06T12:00:00Z", now);
    expect(info.state).toBe("ok");
  });

  it("maps badge classes", () => {
    expect(slaBadgeClass("overdue")).toContain("red");
    expect(slaBadgeClass("soon")).toContain("amber");
  });
});
