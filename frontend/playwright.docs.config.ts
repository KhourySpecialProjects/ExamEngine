import { defineConfig, devices } from "@playwright/test";

/**
 * Docs screenshots (not tests): `npm run docs:screenshots` drives the local dev
 * stack and writes the images used by content/docs. See
 * docs-screenshots/quickstart.screenshots.ts for prerequisites.
 */
export default defineConfig({
  testDir: "./docs-screenshots",
  testMatch: "*.screenshots.ts",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: "list",
  timeout: 5 * 60_000,
  expect: { timeout: 30_000 },
  use: {
    ...devices["Desktop Chrome"],
    baseURL: process.env.DOCS_BASE_URL ?? "http://localhost:3000",
    // Wide enough for the schedules table beside the sidebar; tall enough for
    // the Generate dialog (~1,100 px), which doesn't scroll.
    viewport: { width: 1440, height: 1200 },
    deviceScaleFactor: 2,
    colorScheme: "light",
    locale: "en-US",
    timezoneId: "America/New_York",
  },
  projects: [{ name: "chromium" }],
});
