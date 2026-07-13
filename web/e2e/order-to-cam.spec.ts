import { test, expect } from '@playwright/test';

test.describe('Landing page smoke', () => {
  test('renders hero with brand and CTA', async ({ page }) => {
    await page.goto('/');

    // Название бренда видно в шапке.
    await expect(page.locator('header').getByText('АвтоРаскрой')).toBeVisible();

    // Первый экран показывает актуальный оффер.
    await expect(page.getByRole('heading', { level: 1 })).toContainText(
      'Эскиз клиента — в точный заказ',
    );

    // Основная CTA ведёт в создание заказа.
    const cta = page.getByRole('link', { name: 'Загрузить эскиз' }).first();
    await expect(cta).toBeVisible();
    await expect(cta).toHaveAttribute('href', '/new');
  });

  test('login link navigates to /login', async ({ page }) => {
    await page.goto('/');

    const loginLink = page.locator('header').getByRole('link', { name: 'Войти' });
    await expect(loginLink).toBeVisible();
    await loginLink.click();

    await page.waitForURL(/\/login/);
    expect(page.url()).toContain('/login');
  });
});
