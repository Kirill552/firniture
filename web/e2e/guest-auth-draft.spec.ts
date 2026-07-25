import { test, expect } from '@playwright/test';

test.describe('Guest first auth draft flow', () => {
  test('manual input guest triggers auth gate modal on confirm', async ({ page }) => {
    // Go to new order page
    await page.goto('/new');

    // Click manual entry button
    const manualBtn = page.getByTestId('manual-entry-button');
    await expect(manualBtn).toBeVisible();
    await manualBtn.click();

    // Fill in cabinet params
    // 1. Select cabinet type (e.g. base)
    const baseTypeBtn = page.getByRole('button', { name: /напольная/i }).first();
    await expect(baseTypeBtn).toBeVisible();
    await baseTypeBtn.click();

    // 2. Set dimensions
    const widthInput = page.getByTestId('input-width-mm');
    await widthInput.fill('800');
    const heightInput = page.getByTestId('input-height-mm');
    await heightInput.fill('720');
    const depthInput = page.getByTestId('input-depth-mm');
    await depthInput.fill('560');

    // 3. Click confirm/calculate details
    const confirmBtn = page.getByTestId('confirm-manual-button');
    await expect(confirmBtn).toBeVisible();
    await expect(confirmBtn).toBeEnabled();
    
    // Clicking confirm as a guest should trigger the guest auth gate popup
    await confirmBtn.click();

    // 4. Assert that the GuestAuthGate modal is visible
    const gateHeading = page.locator('h3', { hasText: 'Черновик готов' });
    await expect(gateHeading).toBeVisible();

    const gateText = page.locator('p', { hasText: 'закрепить заказ за вашей фабрикой' });
    await expect(gateText).toBeVisible();

    // 5. Assert that register button redirects to auth page
    const registerBtn = page.getByRole('button', { name: 'Создать аккаунт', exact: true });
    await expect(registerBtn).toBeVisible();
    await registerBtn.click();

    // Verify it redirects to login with expected query params
    await page.waitForURL(/\/login/);
    const url = page.url();
    expect(url).toContain('mode=register');
    expect(url).toContain('entry=save-draft');
    expect(url).toContain('returnTo');
  });
});
