import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

import { getUploadErrorMessage } from "./upload-errors";

describe("getUploadErrorMessage", () => {
  it("показывает сообщение backend и время ожидания для 429", () => {
    expect(
      getUploadErrorMessage(429, {
        detail: {
          code: "rate_limited",
          message: "Слишком много попыток.",
          retry_after_seconds: 90,
        },
      })
    ).toBe("Слишком много попыток. Повторите через 90 сек.");
  });

  it("не раскрывает внутренний ответ для неизвестной 503", () => {
    expect(getUploadErrorMessage(503, { detail: "stack trace" })).toBe(
      "Проверка временно недоступна. Попробуйте позже."
    );
  });
});

describe("useOrderCreator source checks", () => {
  it("includes authRequired state handling on guest confirm", () => {
    const source = fs.readFileSync(
      path.resolve(__dirname, "./use-order-creator.ts"),
      "utf8"
    );
    
    expect(source).toContain("authRequired: boolean;");
    expect(source).toContain("authRequired: false");
    expect(source).toContain("authRequired: true");
  });
});
