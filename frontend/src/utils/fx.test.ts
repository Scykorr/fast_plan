import { describe, expect, it } from "vitest";

import { convertFromBase } from "./fx";

describe("convertFromBase", () => {
  it("returns amount unchanged when currencies match", () => {
    expect(convertFromBase(1000, "RUB", "RUB", { RUB: 1, USD: 90 })).toBe(1000);
  });

  it("converts using rate_to_base", () => {
    expect(convertFromBase(905, "RUB", "USD", { RUB: 1, USD: 90.5 })).toBe(10);
  });

  it("falls back when rate is missing", () => {
    expect(convertFromBase(500, "RUB", "EUR", { RUB: 1 })).toBe(500);
  });
});
