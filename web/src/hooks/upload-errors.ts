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
 
export function getImageExtractErrorMessage(errorType?: string | null): string {
  switch (errorType) {
    case "multiple_modules":
    case "not_furniture_source":
      return "На фото несколько модулей или кухня целиком. Сейчас сервис считает один модуль за раз. Выберите конкретный шкаф или задайте габариты вручную.";
    case "file_too_large":
    case "payload_too_large":
    case "image_too_large":
      return "Файл слишком большой. Загрузите изображение меньшего размера или задайте габариты вручную.";
    case "unsupported_format":
    case "unsupported_file_type":
      return "Формат файла не поддерживается. Загрузите JPG, PNG, WebP или PDF.";
    case "invalid_pdf":
      return "Не удалось прочитать PDF. Проверьте файл или задайте габариты вручную.";
    case "service_unavailable":
      return "Проверка изображения временно недоступна. Задайте габариты вручную.";
    case "ocr_failed":
      return "Не удалось разобрать изображение. Выберите конкретный шкаф или задайте габариты вручную.";
    default:
      return "Не удалось разобрать изображение. Выберите конкретный шкаф или задайте габариты вручную.";
  }
}
