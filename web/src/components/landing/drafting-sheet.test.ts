import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

describe('DraftingSheet', () => {
  it('ограничивает подписи штампа границами ячеек', () => {
    const source = readFileSync(
      new URL('./drafting-sheet.tsx', import.meta.url),
      'utf8',
    );

    expect(source).toContain('data-title-cell="order"');
    expect(source).toContain('data-title-cell="stage"');
    expect(source).toContain('data-title-cell="material"');
    expect(source).toContain('clipPath="url(#title-order-clip)"');
    expect(source).toContain('clipPath="url(#title-stage-clip)"');
    expect(source).toContain('clipPath="url(#title-material-clip)"');
  });
});
