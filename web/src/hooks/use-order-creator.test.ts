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
