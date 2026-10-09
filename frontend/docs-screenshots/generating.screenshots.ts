/**
 * Screenshots for the Generating section (content/docs/generating). Runs after
 * start.screenshots.ts; see that file for prerequisites. Generates one extra
 * schedule (DRAFT) for the progress and result messages and deletes it at the
 * end.
 */
import { expect, type Page, test } from "@playwright/test";
import {
  apiSession,
  CLASSIC,
  DATASET,
  DEMO,
  OPTIMIZED,
  openSchedule,
  shot,
  signIn,
  toast,
} from "./support";

const DRAFT = "Sample schedule (draft)";

/** The generation settings in a schedule page's header. */
const settingsList = (page: Page) =>
  page.locator("dl").filter({ has: page.getByText("Promote to larger rooms") });

test("generating screenshots", async ({ page }) => {
  // With Optimized the dialog grows a row; at the config's height it would
  // scroll and hide the Generate Schedule button.
  await page.setViewportSize({ width: 1440, height: 1400 });
  await signIn(page);

  await test.step("the Generate dialog, Classic and Optimized", async () => {
    // A new browser has no dataset selected.
    await page
      .getByRole("combobox")
      .filter({ hasText: "Choose Dataset" })
      .click();
    await page.getByRole("option", { name: DATASET }).click();
    await expect(page.locator("#generate-id")).toBeEnabled();

    await page.locator("#generate-id").click();
    const dialog = page.getByRole("dialog", { name: "Optimize Exam Schedule" });
    await dialog.locator("#schedule-name").fill(DRAFT);
    await shot(page, dialog, "generate-dialog-classic");

    await dialog
      .getByRole("group", { name: "Algorithm" })
      .getByRole("button", { name: "Optimized" })
      .click();
    await expect(
      dialog.getByRole("group", { name: "Optimization time" }),
    ).toBeVisible();
    await shot(page, dialog, "generate-dialog-optimized");

    // Generate, then close the dialog while it runs: the schedules list shows
    // the new schedule as Running until it is saved.
    await dialog.getByRole("button", { name: "Generate Schedule" }).click();
    const running = toast(page, "Generating schedule...");
    await expect(running).toBeVisible();
    await shot(page, running, "generate-progress-toast", { toasts: true });
    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();
    const row = page
      .locator("#schedule-view")
      .getByRole("row")
      .filter({ hasText: DRAFT });
    await expect(row.getByText("Running")).toBeVisible();
    await shot(page, row, "generate-running-row", { pad: 4 });

    const generated = toast(page, "Schedule generated!");
    await expect(generated).toBeVisible({ timeout: 120_000 });
    await shot(page, generated, "generate-success-toast", { toasts: true });
    await expect(row.getByText("Completed")).toBeVisible();
  });

  await test.step("settings in the schedule header", async () => {
    await openSchedule(page, CLASSIC);
    await expect(settingsList(page)).toBeVisible();
    await shot(page, settingsList(page), "generate-settings-classic", {
      pad: 8,
    });
    await openSchedule(page, OPTIMIZED);
    await expect(settingsList(page)).toBeVisible();
    await shot(page, settingsList(page), "generate-settings-optimized", {
      pad: 8,
    });
  });

  // Leave the demo account as start.screenshots.ts left it.
  const demo = await apiSession(DEMO.email, DEMO.password);
  expect(demo.ok, `demo login (${demo.status})`).toBe(true);
  const schedules = (await (await demo.api.get("schedule")).json()) as {
    schedule_id: string;
    schedule_name: string;
  }[];
  for (const s of schedules.filter((s) => s.schedule_name === DRAFT)) {
    expect((await demo.api.delete(`schedule/${s.schedule_id}`)).ok()).toBe(
      true,
    );
  }
  await demo.api.dispose();
});
