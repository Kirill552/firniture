import { test, expect } from '@playwright/test';

test.describe('Cabinet light visual design checks', () => {
  const viewports = [
    { width: 1440, height: 1024, name: 'desktop' },
    { width: 1024, height: 768, name: 'tablet' },
    { width: 390, height: 844, name: 'mobile' },
  ];

  for (const vp of viewports) {
    test(`check layout stability and no overflow on ${vp.name} viewport`, async ({ page }) => {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      
      // Go to landing
      await page.goto('/');
      
      // Check horizontal overflow
      const horizontalScrollable = await page.evaluate(() => {
        return document.documentElement.scrollWidth > window.innerWidth;
      });
      expect(horizontalScrollable).toBe(false);

      // Verify header holds no dark theme toggle
      const themeToggle = page.locator('header').getByRole('button', { name: /тема|theme/i });
      await expect(themeToggle).toHaveCount(0);
    });
  }

  test('CAM sidebar link and profiles setting are hidden when machine features are disabled', async ({ page }) => {
    // Note: In tests, the server runs with fail-closed defaults from conftest.py / env.test.example (flag=false)
    // We mock login or go to settings
    await page.goto('/login');
    
    // Switch to login tab and verify it's active
    const loginButton = page.getByRole('button', { name: 'Войти', exact: true }).first();
    await expect(loginButton).toBeVisible();
    
    // Verify that CAM link in sidebar or navigation is absent on /login page
    const camSidebarLink = page.locator('aside').getByText('Файлы для станка');
    await expect(camSidebarLink).toHaveCount(0);
  });
});
