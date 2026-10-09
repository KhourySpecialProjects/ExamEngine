import { defineConfig, devices } from "@playwright/test";

/**
 * Docs screenshots (not tests): `npm run docs:screenshots` drives the local dev
 * stack and writes the images used by content/docs. See
 * docs-screenshots/start.screenshots.ts for prerequisites.
 *
 * `start` sets up the demo account and data, every other `*.screenshots.ts`
 * (one per docs section) runs after it, and `wipe` deletes the demo data at the
 * end. A file filter (`npm run docs:screenshots generating`) still runs `start`
 * and `wipe`.
 */
export default defineConfig({
  testDir: "./docs-screenshots",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: "list",
  timeout: 3 * 60_000,
  expect: { timeout: 30_000 },
  use: {
    ...devices["Desktop Chrome"],
    baseURL: process.env.DOCS_BASE_URL ?? "http://localhost:3000",
    // Wide enough for the schedules table beside the sidebar; tall enough to
    // show the whole Generate dialog (~1,100 px) without scrolling.
    viewport: { width: 1440, height: 1200 },
    deviceScaleFactor: 2,
    colorScheme: "light",
    locale: "en-US",
    timezoneId: "America/New_York",
  },
  projects: [
    { name: "start", testMatch: "start.screenshots.ts", teardown: "wipe" },
    {
      name: "sections",
      testMatch: "*.screenshots.ts",
      testIgnore: "start.screenshots.ts",
      dependencies: ["start"],
    },
    { name: "wipe", testMatch: "wipe.teardown.ts" },
  ],
});
