import { defineConfig } from "@playwright/test";

const isCI = !!process.env.CI;

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  retries: isCI ? 1 : 0,
  reporter: isCI ? "github" : "list",
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "chromium", use: { browserName: "chromium" } },
  ],
  webServer: {
    // In CI we expect a prior build step; start only. Locally allow build.
    command: isCI ? "npm run start" : "npm run build && npm start",
    url: "http://localhost:3000",
    reuseExistingServer: !isCI,
    timeout: 180_000,
    env: {
      NODE_ENV: "production",
    },
  },
});
