/**
 * Screenshots for "Reviewing a schedule", part 1 (content/docs/reviewing):
 * the schedules list, the schedule page header, the Density, Compact and List
 * views, the cell dialog and Statistics. See start.screenshots.ts for the
 * prerequisites and the data this file starts from.
 *
 * For the "Deleted" dataset badge it uploads a second copy of the sample
 * files, generates a schedule from it and deletes that dataset; the schedule
 * is deleted again at the end.
 */
import { readFile } from "node:fs/promises";
import path from "node:path";
import { expect, type Page, test } from "@playwright/test";
import {
  apiSession,
  CLASSIC,
  DEMO,
  OPTIMIZED,
  SAMPLE_DIR,
  SAMPLE_FILES,
  shot,
  signIn,
  toast,
} from "./support";

const OLD_DATASET = "Old sample data";
const OLD_SCHEDULE = "Old sample schedule";

/** The view root (a `space-y-4` block) holding this heading. */
const viewRoot = (page: Page, heading: string) =>
  page
    .locator("div.space-y-4")
    .filter({ has: page.getByRole("heading", { name: heading }) })
    .first();

test("reviewing a schedule, part 1", async ({ page }) => {
  const demo = await apiSession(DEMO.email, DEMO.password);
  expect(demo.ok, `demo login (${demo.status})`).toBe(true);
  await signIn(page);

  await test.step("a schedule whose dataset was deleted", async () => {
    await page.locator("#upload-id").click();
    const upload = page.getByRole("dialog", { name: "Upload Dataset" });
    await upload.locator("#dataset-name").fill(OLD_DATASET);
    const inputs = upload.locator('input[type="file"]');
    for (const [i, file] of SAMPLE_FILES.entries()) {
      await inputs.nth(i).setInputFiles(path.join(SAMPLE_DIR, `${file}.csv`));
    }
    await upload.getByRole("button", { name: "Upload All Files" }).click();
    await expect(
      upload.getByText("All files uploaded successfully!"),
    ).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(upload).toBeHidden();

    await page.locator("#generate-id").click();
    const generate = page.getByRole("dialog", {
      name: "Optimize Exam Schedule",
    });
    await generate.locator("#schedule-name").fill(OLD_SCHEDULE);
    await generate.getByRole("button", { name: "Generate Schedule" }).click();
    await expect(toast(page, "Schedule generated!")).toBeVisible({
      timeout: 120_000,
    });
    await page.keyboard.press("Escape");
    await expect(generate).toBeHidden();

    const schedules = (await (await demo.api.get("schedule")).json()) as {
      schedule_name: string;
      dataset_id: string;
    }[];
    const old = schedules.find((s) => s.schedule_name === OLD_SCHEDULE);
    expect(old, OLD_SCHEDULE).toBeTruthy();
    const deleted = await demo.api.delete(`datasets/${old?.dataset_id}`);
    expect(deleted.ok(), `delete ${OLD_DATASET}`).toBe(true);
  });

  await test.step("the schedules list", async () => {
    await page.goto("/dashboard");
    const list = page.locator("#schedule-view");
    await expect(list.getByRole("link", { name: OLD_SCHEDULE })).toBeVisible();
    await expect(list.getByText("Deleted", { exact: true })).toBeVisible();
    await shot(page, list, "review-schedules-list");

    // Not by role: while the menu is open, Radix hides the rest from ARIA.
    const columns = list.locator("button", { hasText: "Columns" });
    await columns.click();
    const menu = page.getByRole("menu");
    await expect(menu).toBeVisible();
    await shot(page, [columns, menu], "review-columns-menu", { pad: 8 });
    await page.keyboard.press("Escape");
    await expect(menu).toBeHidden();

    for (const name of [CLASSIC, OPTIMIZED]) {
      await list.getByRole("checkbox", { name: `Select ${name}` }).click();
    }
    const bar = page.getByRole("region", { name: "Selected schedules" });
    await expect(bar.getByText("2 selected")).toBeVisible();
    await shot(page, bar, "review-compare-bar", { pad: 12 });
    await bar.getByRole("button", { name: "Clear" }).click();
    await expect(bar).toBeHidden();

    await list
      .getByRole("row", { name: new RegExp(OLD_SCHEDULE) })
      .getByRole("button", { name: "Open menu" })
      .click();
    await page.getByRole("menuitem", { name: "Delete" }).click();
    const confirm = page.getByRole("alertdialog");
    await expect(confirm).toBeVisible();
    await shot(page, confirm, "review-delete-schedule");
    await confirm.getByRole("button", { name: "Cancel" }).click();
    await expect(confirm).toBeHidden();

    await list.getByRole("button", { name: "By dataset" }).click();
    await list.getByRole("button", { name: "Expand all" }).click();
    await expect(
      list.getByRole("region", { name: OLD_DATASET }).getByRole("table"),
    ).toBeVisible();
    await shot(page, list, "review-by-dataset");
    await list.getByRole("button", { name: "List", exact: true }).click();
  });

  await test.step("the schedule page", async () => {
    const list = page.locator("#schedule-view");
    await list.getByRole("link", { name: CLASSIC }).click();
    await page.waitForURL(/\/dashboard\/[0-9a-f-]+/);
    const header = page
      .locator('[data-slot="card"]')
      .filter({ hasText: "Exam blocks per day" });
    await expect(header).toBeVisible();
    await shot(page, header, "review-schedule-header", { pad: 8 });
  });

  await test.step("Density, the cell dialog and Compact", async () => {
    // The calendars are wider than the page beside the sidebar: collapse it,
    // so all seven days fit.
    await page.getByRole("button", { name: "Collapse sidebar" }).click();
    await expect(
      page.getByRole("button", { name: "Expand sidebar" }),
    ).toBeVisible();
    const density = viewRoot(page, "Density View");
    await expect(density.getByText("Density Legend (Exams)")).toBeVisible();
    await shot(page, density, "review-density", { pad: 8 });

    // The busiest cell gives the fullest dialog.
    const labels = await density.getByText(/^\d+ Exams?$/).allTextContents();
    const busiest = labels.sort(
      (a, b) => Number.parseInt(b, 10) - Number.parseInt(a, 10),
    )[0];
    await density.getByText(busiest, { exact: true }).first().click();
    const dialog = page.getByRole("dialog");
    await expect(dialog.getByText("exams scheduled")).toBeVisible();
    await shot(page, dialog, "review-cell-dialog", { maxHeight: 820 });
    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();

    await page.getByRole("tab", { name: "Compact" }).click();
    expect(page.url()).toContain("view=compact");
    const compact = viewRoot(page, "Compact View");
    await expect(compact.locator("table")).toBeVisible();
    await shot(page, compact, "review-compact", { pad: 8, maxHeight: 1000 });
  });

  await test.step("List", async () => {
    await page.getByRole("tab", { name: "List" }).click();
    const list = viewRoot(page, "List View");
    // Sorting by day puts the unscheduled exams (no day) first.
    await list.getByRole("button", { name: "Day" }).click();
    await expect(list.getByText("Unscheduled").first()).toBeVisible();
    await shot(page, list, "review-list-view", { pad: 8 });
  });

  await test.step("Statistics", async () => {
    await page.getByRole("tab", { name: "Statistics" }).click();
    const overview = page.locator('section[aria-labelledby="stats-overview"]');
    const groups = page.locator('section[aria-labelledby="stats-groups"]');
    await expect(groups).toBeVisible();
    await shot(page, [overview, groups], "review-statistics-overview", {
      pad: 8,
    });
    const distribution = page.locator(
      'section[aria-labelledby="stats-distribution"]',
    );
    await distribution.scrollIntoViewIfNeeded();
    // Let the bar charts finish their entrance animation.
    await page.waitForTimeout(1500);
    await shot(page, distribution, "review-statistics-distribution", {
      pad: 8,
    });
  });

  await test.step("export", async () => {
    const download = page.waitForEvent("download");
    await page.getByRole("button", { name: "Export Schedule" }).click();
    const file = await download;
    expect(file.suggestedFilename()).toBe("schedule_exams.csv");
    const csv = await readFile(await file.path(), "utf8");
    const [headerLine, ...rows] = csv.split("\n");
    // The columns and value formats that docs/reviewing/exporting describes.
    expect(headerLine).toBe(
      "CRN,Course,Day,Start Time,End Time,Room,Capacity,Size,Valid,Instructor",
    );
    expect(rows).toContain("20001,MATH 1005,,,,,0,121,true,Dr. B3");
    for (const row of rows.filter((r) => !r.includes(",,"))) {
      expect(row).toMatch(
        /^\d+,[A-Z]+ \d+,[A-Z][a-z]+day,\d\d:\d\d,\d\d:\d\d,Room \d+,\d+,\d+,(true|false),Dr\. \w+$/,
      );
    }
  });

  // Leave the demo account as start.screenshots.ts left it.
  const schedules = (await (await demo.api.get("schedule")).json()) as {
    schedule_id: string;
    schedule_name: string;
  }[];
  for (const s of schedules.filter((s) => s.schedule_name === OLD_SCHEDULE)) {
    await demo.api.delete(`schedule/${s.schedule_id}`);
  }
  await demo.api.dispose();
});
