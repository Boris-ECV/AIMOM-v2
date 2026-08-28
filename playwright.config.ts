import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:4173",
    trace: "on-first-retry",
  },
  webServer: [
    {
      command: "python src/tests/e2e_server.py",
      url: "http://127.0.0.1:8000/api/health",
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
    },
    {
      command: "python -m http.server 4173 --directory src/frontend",
      url: "http://127.0.0.1:4173/index.html",
      reuseExistingServer: !process.env.CI,
      timeout: 15_000,
    },
  ],
});
