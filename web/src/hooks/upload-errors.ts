interface UploadErrorEnvelope {
  detail?: {
    code?: string;
    message?: string;
    retry_after_seconds?: number | null;
  } | string;
}

export function getUploadErrorMessage(status: number, payload: unknown): string {
  const envelope = payload && typeof payload === "object" ? payload as UploadErrorEnvelope : {};
  const detail = envelope.detail && typeof envelope.detail === "object" ? envelope.detail : null;
  if (detail?.message) {
    if (status === 429 && detail.retry_after_seconds) {
      return `${detail.message} Повторите через ${detail.retry_after_seconds} сек.`;
    }
    return detail.message;
  }
  if (status === 413) return "Файл слишком большой. Максимальный размер — 10 МБ.";
  if (status === 415) return "Поддерживаются JPG, PNG, WebP и PDF.";
  if (status === 429) return "Слишком много попыток. Повторите позже.";
  if (status === 503) return "Проверка временно недоступна. Попробуйте позже.";
  return "Не удалось проверить файл. Попробуйте другой исходник.";
}
