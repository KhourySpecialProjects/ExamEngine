import { expect, test } from "@playwright/test";
import { apiSession, DEMO, wipeDemo } from "./support";

// Runs after every section (playwright.docs.config.ts): the demo account keeps
// no data between runs.
test("wipe the demo account", async () => {
  const demo = await apiSession(DEMO.email, DEMO.password);
  expect(demo.ok, `demo login (${demo.status})`).toBe(true);
  await wipeDemo(demo.api);
  await demo.api.dispose();
});
