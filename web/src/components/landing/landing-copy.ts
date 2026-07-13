/**
 * Единый источник правды для копирайта лендинга АвтоРаскрой.
 * Только русский, честный copy без запрещённых обещаний.
 * Используется в hero, stages, output, tests.
 */

export type StageId = 1 | 2 | 3 | 4 | 5;

export interface Stage {
  id: StageId;
  title: string;
  description: string;
}

export const LANDING_COPY = {
  brand: "АвтоРаскрой",

  // Первый экран.
  heroOverline: "Рабочий инструмент мебельного технолога",
  h1: "Эскиз клиента — в точный заказ",
  heroDescription:
    "Загрузите фото или PDF. АвтоРаскрой снимет размеры, покажет спорные места и соберёт спецификацию. Вы проверяете результат — сервис формирует DXF и PDF.",
  ctaPrimary: "Загрузить эскиз",
  ctaHint:
    "Без регистрации: распознавание и вопросы по эскизу · один файл до 10 МБ",

  // Навигационные якоря.
  navHow: "Как работает",
  navCapabilities: "Возможности",
  navLogin: "Войти",

  // Блок результата.
  resultTitle: "Проверяемый результат: спецификация, DXF и PDF",
  resultDescription:
    "Без регистрации можно распознать эскиз и проверить параметры. После входа и вашего подтверждения сервис подготовит спецификацию, DXF и PDF.",

  // Финальный CTA.
  finalCtaTitle: "Попробуйте на заказе, который разбираете сейчас",
  finalCtaHint: "Распознавание и предварительная проверка доступны без регистрации.",

  // Подвал.
  footerCopyright: "АвтоРаскрой © 2026",
} as const;

export const STAGES: Stage[] = [
  {
    id: 1,
    title: "Загрузите эскиз клиента",
    description: "Фото, скриншот или PDF с одним мебельным модулем.",
  },
  {
    id: 2,
    title: "Проверьте, что распознал сервис",
    description: "Размеры и материалы показаны рядом с исходником.",
  },
  {
    id: 3,
    title: "Ответьте на важные вопросы",
    description: "Спросим только о параметрах, которые меняют расчёт.",
  },
  {
    id: 4,
    title: "Сверьте спецификацию",
    description: "Исправьте панели, кромку и фурнитуру до подтверждения.",
  },
  {
    id: 5,
    title: "Скачайте DXF и PDF",
    description: "После входа и вашего подтверждения сервис сформирует документы.",
  },
];

// Для SSR и тестов: полный текст этапа (title + description)
export function getStageText(stage: Stage): string {
  return `${stage.title}. ${stage.description}`;
}

// Проверка отсутствия запрещённых фраз (для тестов)
const FORBIDDEN_PHRASES = [
  "30 секунд",
  "за 30 секунд",
  "готово для станка",
  "G-code",
  "программа ЧПУ",
  "готовые файлы для станка",
  "ЧПУ готова",
];

export function containsForbidden(text: string): boolean {
  const lower = text.toLowerCase();
  return FORBIDDEN_PHRASES.some((p) => lower.includes(p.toLowerCase()));
}

// Экспорт констант для тестов
export const FORBIDDEN = FORBIDDEN_PHRASES;
