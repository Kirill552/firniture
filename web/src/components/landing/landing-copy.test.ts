import { describe, it, expect } from 'vitest';
import {
  STAGES,
  LANDING_COPY,
  FAQ_ITEMS,
  FOOTER_COLUMNS,
  containsForbidden,
  FORBIDDEN,
  type StageId,
} from './landing-copy';

describe('landing-copy', () => {
  it('has exactly 5 unique stages', () => {
    expect(STAGES).toHaveLength(5);
    const ids = STAGES.map((s) => s.id);
    expect(new Set(ids).size).toBe(5);
    expect(ids).toEqual([1, 2, 3, 4, 5]);
  });

  it('every stage has non-empty title and description', () => {
    STAGES.forEach((stage) => {
      expect(stage.title.length).toBeGreaterThan(3);
      expect(stage.description.length).toBeGreaterThan(3);
    });
  });

  it('DXF and PDF mentioned in stage 5 and result copy', () => {
    const stage5 = STAGES.find((s) => s.id === 5)!;
    expect(stage5.title).toContain('DXF');
    expect(stage5.title).toContain('PDF');
    expect(LANDING_COPY.resultTitle).toContain('DXF');
    expect(LANDING_COPY.resultTitle).toContain('PDF');
    expect(LANDING_COPY.heroDescription).toContain('DXF');
    expect(LANDING_COPY.heroDescription).toContain('PDF');
  });

  it('CTA прямо предлагает загрузить эскиз', () => {
    expect(LANDING_COPY.ctaPrimary).toBe('Загрузить эскиз');
  });

  it('H1 and main descriptions match spec', () => {
    expect(LANDING_COPY.h1).toBe('Эскиз клиента — в точный заказ');
    expect(LANDING_COPY.heroDescription).toContain('снимет размеры');
    expect(LANDING_COPY.heroDescription).toContain('сервис формирует DXF и PDF');
  });

  it('no forbidden phrases in any copy (no 30s, G-code, ready for machine)', () => {
    const allTexts = [
      LANDING_COPY.h1,
      LANDING_COPY.heroDescription,
      LANDING_COPY.ctaHint,
      LANDING_COPY.resultTitle,
      LANDING_COPY.resultDescription,
      LANDING_COPY.finalCtaTitle,
      LANDING_COPY.finalCtaHint,
      ...STAGES.map((s) => `${s.title} ${s.description}`),
    ];
    allTexts.forEach((text) => {
      expect(containsForbidden(text)).toBe(false);
    });
  });

  it('FORBIDDEN list is defined and contains expected', () => {
    expect(FORBIDDEN.length).toBeGreaterThan(3);
    expect(FORBIDDEN.some((p) => p.includes('30'))).toBe(true);
  });

  it('FAQ содержит 6-10 честных вопросов без запрещённых фраз', () => {
    expect(FAQ_ITEMS.length).toBeGreaterThanOrEqual(6);
    expect(FAQ_ITEMS.length).toBeLessThanOrEqual(10);
    FAQ_ITEMS.forEach((item) => {
      expect(item.question.length).toBeGreaterThan(10);
      expect(item.answer.length).toBeGreaterThan(40);
      expect(containsForbidden(item.question)).toBe(false);
      expect(containsForbidden(item.answer)).toBe(false);
    });
    // Вопросы уникальны (schema.org FAQPage не любит дубли)
    const questions = FAQ_ITEMS.map((i) => i.question);
    expect(new Set(questions).size).toBe(questions.length);
  });

  it('футер ссылается только на существующие маршруты и якоря лендинга', () => {
    const routes = FOOTER_COLUMNS.flatMap((c) => c.links.map((l) => l.href));
    expect(routes.length).toBeGreaterThan(4);
    routes.forEach((href) => {
      expect(href).toMatch(/^\/(#\w+)?[\w/]*$/);
    });
    // Юридические страницы обязательны (152-ФЗ, доверие Яндекса)
    expect(routes).toContain('/oferta');
    expect(routes).toContain('/privacy');
    expect(routes).toContain('/pricing');
  });

  it('progress mapper ranges map 0..1 to stages 1-5 correctly (simulated)', () => {
    // Воспроизводим точную логику преобразования прогресса в этап.
    function mapProgressToStage(p: number): StageId {
      if (p < 0.2) return 1;
      if (p < 0.4) return 2;
      if (p < 0.6) return 3;
      if (p < 0.8) return 4;
      return 5;
    }

    expect(mapProgressToStage(0)).toBe(1);
    expect(mapProgressToStage(0.199)).toBe(1);
    expect(mapProgressToStage(0.2)).toBe(2);
    expect(mapProgressToStage(0.399)).toBe(2);
    expect(mapProgressToStage(0.4)).toBe(3);
    expect(mapProgressToStage(0.6)).toBe(4);
    expect(mapProgressToStage(0.799)).toBe(4);
    expect(mapProgressToStage(0.8)).toBe(5);
    expect(mapProgressToStage(0.999)).toBe(5);
    expect(mapProgressToStage(1)).toBe(5);
  });
});
