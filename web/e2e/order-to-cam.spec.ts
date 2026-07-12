import { test, expect } from "@playwright/test";

test.describe("Landing page smoke", () => {
  test("renders hero with brand and CTA", async ({ page }) => {
    await page.goto("/");

    // Brand name is visible in header
    await expect(page.locator("header").getByText("АвтоРаскрой")).toBeVisible();

    // Hero headline renders
    await expect(
      page.getByText("Фото эскиза → файлы для станка"),
    ).toBeVisible();

    // Primary CTA is present and links to /new
    const cta = page.getByRole("link", { name: "Попробовать бесплатно" }).first();
    await expect(cta).toBeVisible();
    await expect(cta).toHaveAttribute("href", "/new");
  });

  test("login link navigates to /login", async ({ page }) => {
    await page.goto("/");

    const loginLink = page.locator("header").getByRole("link", { name: "Войти" });
    await expect(loginLink).toBeVisible();
    await loginLink.click();

    await page.waitForURL(/\/login/);
    expect(page.url()).toContain("/login");
  });
});
