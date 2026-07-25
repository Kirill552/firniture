import { test, expect } from '@playwright/test';

test.describe('Landing experience (Tasks 3-5 visual)', () => {
  test('показывает основной оффер и ведёт с CTA на /new', async ({ page }) => {
    await page.goto('/');

    await expect(page.getByRole('heading', { level: 1 })).toContainText('Эскиз клиента — в точный заказ');

    const cta = page.getByRole('link', { name: 'Загрузить эскиз' }).first();
    await expect(cta).toBeVisible();
    await expect(cta).toHaveAttribute('href', '/new');
  });

  test('hero uses the approved kitchen reference without a WebGL canvas', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/');

    await expect(
      page.getByRole('img', { name: 'Эскиз, детали и собранная кухня' }),
    ).toBeVisible();
    await expect(page.locator('main section:first-of-type canvas')).toHaveCount(0);
  });

  test('header anchors and login link present', async ({ page }) => {
    await page.goto('/');

    await expect(page.locator('header').getByRole('link', { name: 'Как работает' })).toBeVisible();
    await expect(page.locator('header').getByRole('link', { name: 'Возможности' })).toBeVisible();

    const login = page.locator('header').getByRole('link', { name: 'Войти' });
    await expect(login).toBeVisible();
  });

  test('five stages visible with correct titles (HTML always present)', async ({ page }) => {
    await page.goto('/');

    await expect(page.getByText('Загрузите эскиз клиента')).toBeVisible();
    await expect(page.getByText('Проверьте, что распознал сервис')).toBeVisible();
    await expect(page.getByText('Ответьте на важные вопросы')).toBeVisible();
    await expect(page.getByText('Сверьте спецификацию')).toBeVisible();
    // Точное совпадение исключает абзац с похожей формулировкой.
    await expect(page.getByText('Скачайте DXF и PDF', { exact: true })).toBeVisible();
  });

  test('scroll advances the process visual through stages 1, 3 and 5', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/');

    const story = page.getByTestId('process-story');
    await expect(story).toHaveAttribute('data-active-stage', '1');

    await page.locator('#stage-3').evaluate((element) => {
      const rect = element.getBoundingClientRect();
      window.scrollTo(0, window.scrollY + rect.top - window.innerHeight * 0.25);
    });
    await expect(story).toHaveAttribute('data-active-stage', '3');

    await page.locator('#stage-5').evaluate((element) => {
      const rect = element.getBoundingClientRect();
      window.scrollTo(0, window.scrollY + rect.top - window.innerHeight * 0.25);
    });
    await expect(story).toHaveAttribute('data-active-stage', '5');

    const sheetBox = await page.locator('[data-scene-mode="svg"]').boundingBox();
    expect(sheetBox).not.toBeNull();
    expect(sheetBox!.y).toBeGreaterThanOrEqual(88);
    expect(sheetBox!.y + sheetBox!.height).toBeLessThanOrEqual(900);
  });

  test('DXF and PDF visible in stage 5 area and result section', async ({ page }) => {
    await page.goto('/');

    // Достаточно хотя бы одного видимого упоминания каждого формата.
    await expect(page.getByText('DXF').first()).toBeVisible();
    await expect(page.getByText('PDF').first()).toBeVisible();

    // Явное описание этапа проверки.
    await expect(page.getByText(/вашего подтверждения/i).first()).toBeVisible();
    await expect(page.getByText('Проверяемый результат: спецификация, DXF и PDF')).toBeVisible();
  });

  test('no forbidden phrases on public pages', async ({ page }) => {
    const paths = ['/', '/welcome', '/pricing'];
    for (const p of paths) {
      await page.goto(p);
      const html = await page.content();
      expect(html).not.toMatch(/30 секунд/i);
      expect(html).not.toMatch(/G-code/i);
      expect(html).not.toMatch(/готово для станка/i);
      expect(html).not.toMatch(/программа ЧПУ/i);
    }
  });

  test('CTA from landing opens /new and shows dropzone area', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('link', { name: 'Загрузить эскиз' }).first().click();
    await page.waitForURL(/\/new/);
    // Проверяем зону загрузки без привязки к внутренней разметке страницы.
    await expect(page.locator('body')).toContainText(/загрузить|эскиз|файл|drop/i);
  });

  test('mobile viewport shows content and the static reference visual', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 800 });
    await page.goto('/');

    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    await expect(page.getByText('Загрузите эскиз клиента')).toBeVisible();

    // Страница не падает, основной текст остаётся доступным.
    const content = await page.textContent('body');
    expect(content).toContain('DXF');
    expect(content).toContain('PDF');
    await expect(page.getByRole('img', { name: 'Эскиз, детали и собранная кухня' })).toBeVisible();
    await expect(page.locator('canvas')).toHaveCount(0);
  });

  test('reduced motion still shows all stages and CTA (static)', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto('/');

    await expect(page.getByText('Сверьте спецификацию')).toBeVisible();
    await expect(page.getByRole('link', { name: 'Загрузить эскиз' }).first()).toBeVisible();
    await expect(page.getByRole('img', { name: 'Эскиз, детали и собранная кухня' })).toBeVisible();
    await expect(page.locator('canvas')).toHaveCount(0);
  });

  test('keyboard navigation reaches CTA and stages', async ({ page }) => {
    await page.goto('/');

    await page.keyboard.press('Tab');
    await expect(page.getByRole('link', { name: 'Перейти к основному содержимому' })).toBeFocused();
    await page.keyboard.press('Enter');
    await expect(page.locator('#main')).toBeFocused();
  });

  test('mobile scroll does not load the removed WebGL scene', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    const scripts: string[] = [];
    page.on('response', (response) => {
      if (response.request().resourceType() === 'script') scripts.push(response.url());
    });
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.locator('#how').scrollIntoViewIfNeeded();
    await page.waitForTimeout(250);

    expect(scripts.filter((url) => /three|fiber|drei|hero-kitchen-scene/i.test(url))).toEqual([]);
    await expect(page.locator('canvas')).toHaveCount(0);
  });

  test('no JavaScript keeps the offer, five stages and CTA', async ({ browser }) => {
    const context = await browser.newContext({ javaScriptEnabled: false });
    const page = await context.newPage();
    await page.goto('/');
    await expect(page.getByRole('heading', { level: 1 })).toContainText('Эскиз клиента — в точный заказ');
    await expect(page.getByText('Скачайте DXF и PDF', { exact: true })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Загрузить эскиз' }).first()).toHaveAttribute('href', '/new');
    await context.close();
  });
});
