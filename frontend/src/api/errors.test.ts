import { describe, expect, it } from "vitest";

import { ApiError } from "./client";
import { parseApiError } from "./errors";

describe("parseApiError", () => {
  it("returns detail message from API error", () => {
    const error = new ApiError(400, { detail: "Некорректный запрос" });
    expect(parseApiError(error)).toBe("Некорректный запрос");
  });

  it("formats field validation errors", () => {
    const error = new ApiError(400, { email: ["Введите корректный email."] });
    expect(parseApiError(error)).toBe("email: Введите корректный email.");
  });

  it("returns fallback for unknown errors", () => {
    expect(parseApiError(new Error("boom"), "Ошибка")).toBe("Ошибка");
  });
});
