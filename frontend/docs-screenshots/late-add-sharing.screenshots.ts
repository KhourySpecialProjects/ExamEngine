/**
 * Screenshots for "Late Add" (changing/late-add) and "Sharing"
 * (working-with-others/sharing). Runs after start.screenshots.ts (see its
 * header for prerequisites), on the demo account's Classic sample schedule.
 *
 * The late-add exam is the sample's enrollment-only CRN (gen_test_data.py
 * --late-adds, see AGENTS.md). The test saves one late-add version and shares
 * the Classic schedule with the docs-viewer@ account (created and approved
 * here); both are removed before it ends.
 */
import {
  type APIRequestContext,
  expect,
  type Page,
  test,
} from "@playwright/test";
import {
  ADMIN,
  apiSession,
  CLASSIC,
  DEMO,
  ensureAccount,
  shot,
  signIn,
  toast,
  VIEWER,
} from "./support";

const LATE = {
  crn: "20055",
  course_code: "MATH 1020",
  instructor_id: "Dr. B4",
};
const VERSION = `${CLASSIC} + ${LATE.crn}`;

type ScheduleItem = {
  schedule_id: string;
  schedule_name: string;
  is_owner?: boolean;
};

async function scheduleId(api: APIRequestContext, name: string) {
  const schedules = (await (
    await api.get("schedule")
  ).json()) as ScheduleItem[];
  const found = schedules.find((s) => s.schedule_name === name && s.is_owner);
  if (!found) throw new Error(`schedule ${name} not found`);
  return found.schedule_id;
}

/** Remove every share of the Classic schedule and every late-add version. */
async function cleanUp(api: APIRequestContext) {
  const classic = await scheduleId(api, CLASSIC);
  const shares = await (await api.get(`schedule/${classic}/shares`)).json();
  for (const share of shares as { share_id: string }[]) {
    await api.delete(`schedule/shares/${share.share_id}`);
  }
  const schedules = (await (
    await api.get("schedule")
  ).json()) as ScheduleItem[];
  for (const s of schedules) {
    if (s.is_owner && s.schedule_name.startsWith(`${CLASSIC} +`)) {
      await api.delete(`schedule/${s.schedule_id}`);
    }
  }
}

/** Open Late Add on the current schedule page and search for the sample CRN. */
async function searchLateAdd(page: Page) {
  await page.getByRole("button", { name: "Late Add", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: `Late Add: ${CLASSIC}` });
  await dialog.locator("#late-add-crn").fill(LATE.crn);
  await dialog.locator("#late-add-course_code").fill(LATE.course_code);
  await dialog.locator("#late-add-instructor_id").fill(LATE.instructor_id);
  await dialog.getByRole("button", { name: "Find blocks" }).click();
  await expect(dialog.getByText("Clear blocks found")).toBeVisible();
  return dialog;
}

/** The innermost row holding both the view tabs and the action buttons. */
function toolbar(page: Page) {
  return page
    .locator("div")
    .filter({ has: page.getByRole("tablist") })
    .filter({ has: page.getByRole("button", { name: "Export Schedule" }) })
    .last();
}

test("late add and sharing screenshots", async ({ page }) => {
  const admin = await apiSession(ADMIN.email, ADMIN.password);
  expect(admin.ok, `admin login (${admin.status})`).toBe(true);
  await ensureAccount(admin.api, VIEWER, true);
  const demo = await apiSession(DEMO.email, DEMO.password);
  expect(demo.ok, `demo login (${demo.status})`).toBe(true);
  await cleanUp(demo.api);
  // By ID: once the late-add version exists, its name contains CLASSIC.
  const classicUrl = `/dashboard/${await scheduleId(demo.api, CLASSIC)}`;
  const openClassic = async () => {
    await page.goto(classicUrl);
    await expect(
      page.getByRole("button", { name: "Export Schedule" }),
    ).toBeVisible();
    await expect(page.getByText(CLASSIC).first()).toBeVisible();
  };

  try {
    await signIn(page);

    await test.step("save a late-add version", async () => {
      await openClassic();
      const dialog = await searchLateAdd(page);
      const save = dialog.getByRole("form", { name: "Save as new schedule" });
      await expect(save.locator("#late-add-schedule-name")).toHaveValue(
        VERSION,
      );
      await save.getByRole("button", { name: "Save as new schedule" }).click();
      await expect(toast(page, `Saved ${VERSION}`)).toBeVisible();
      await expect(dialog).toBeHidden();
      await expect(
        page.getByRole("link", { name: CLASSIC, exact: true }).first(),
      ).toBeVisible();

      const details = page
        .locator('[data-slot="card"]')
        .filter({ hasText: "Late add to" });
      await expect(
        details.getByRole("table", { name: "Late additions" }),
      ).toBeVisible();
      await shot(page, details, "late-add-version");
    });

    await test.step("search results and the save form", async () => {
      await openClassic();
      const dialog = await searchLateAdd(page);
      const first = dialog
        .getByRole("list", { name: "Blocks, best first" })
        .getByRole("listitem")
        .first();
      // The conflict list's first toggle (the room picker has aria-expanded too).
      const conflict = first.locator("ul button[aria-expanded]").first();
      await conflict.click();
      await expect(conflict).toHaveAttribute("aria-expanded", "true");

      // Crop the dialog above the save form.
      const save = dialog.getByRole("form", { name: "Save as new schedule" });
      await expect(save.getByText("already has a newer version")).toBeVisible();
      const top = (await dialog.boundingBox())?.y ?? 0;
      const saveTop = (await save.boundingBox())?.y ?? 0;
      await shot(page, dialog, "late-add-results", {
        maxHeight: saveTop - top,
      });
      await shot(page, save, "late-add-save", { pad: 8 });

      // One student's exams with the proposed late add.
      await first
        .locator('button[aria-label^="View exams for"]')
        .first()
        .click();
      const exams = page.getByRole("dialog", { name: /^Exams for / });
      await expect(exams.getByText("Proposed")).toBeVisible();
      await shot(page, exams, "late-add-person-exams");
      await page.keyboard.press("Escape");
      await expect(exams).toBeHidden();
      await expect(dialog).toBeVisible();
      await page.keyboard.press("Escape");
      await expect(dialog).toBeHidden();
    });

    await test.step("share the schedule", async () => {
      await page.getByRole("button", { name: "Share", exact: true }).click();
      const dialog = page.getByRole("dialog", {
        name: `Share Schedule: ${CLASSIC}`,
      });
      // The list holds every approved user: never in a screenshot.
      await dialog.getByRole("combobox").click();
      await page.getByRole("option", { name: new RegExp(VIEWER.name) }).click();
      await dialog.getByRole("button", { name: "Share Schedule" }).click();
      await expect(toast(page, "Schedule shared successfully")).toBeVisible();
      await expect(dialog.getByText("Current Shares (1)")).toBeVisible();
      await expect(dialog.getByText(VIEWER.email)).toBeVisible();
      await shot(page, dialog, "sharing-dialog");
      await page.keyboard.press("Escape");
      await expect(dialog).toBeHidden();
    });

    await test.step("what the recipient sees", async () => {
      await page.context().clearCookies();
      await page.evaluate(() => {
        localStorage.clear();
        sessionStorage.clear();
      });
      await signIn(page, VIEWER);
      const list = page.locator("#schedule-view");
      await expect(list.getByText(`Shared by ${DEMO.name}`)).toBeVisible();
      await shot(page, list, "sharing-recipient-list");

      await openClassic();
      await expect(
        page.getByRole("button", { name: "Validate Schedule" }),
      ).toBeVisible();
      await shot(page, toolbar(page), "sharing-recipient-toolbar", { pad: 8 });
    });
  } finally {
    await cleanUp(demo.api);
    await demo.api.dispose();
    await admin.api.dispose();
  }
});
