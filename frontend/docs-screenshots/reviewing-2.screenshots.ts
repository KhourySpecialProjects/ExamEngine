/**
 * Screenshots for "Reviewing a schedule", part 2 (content/docs/reviewing:
 * conflicts, explore, validating, comparing). Runs after start.screenshots.ts,
 * which leaves the demo account with DATASET, CLASSIC and OPTIMIZED.
 *
 * The sample schedules have no double-bookings, so this file also generates
 * TWO_DAYS (Classic, two exam days) for the Conflicts tab, the course conflict
 * dialog and the person popup, and deletes it at the end. Running the
 * Validator changes nothing (its result is only shown in the dialog).
 */
import { expect, type Locator, type Page, test } from "@playwright/test";
import {
  apiSession,
  CLASSIC,
  DATASET,
  DEMO,
  OPTIMIZED,
  shot,
  signIn,
} from "./support";

const TWO_DAYS = "Sample schedule (Two days)";

type Listed = { schedule_id: string; schedule_name: string };

/** The schedule page's content card holding a control (Explore, Conflicts). */
const cardWith = (page: Page, control: Locator) =>
  page.locator('[data-slot="card"]').filter({ has: control });

test("docs screenshots: reviewing part 2", async ({ page }) => {
  const demo = await apiSession(DEMO.email, DEMO.password);
  expect(demo.ok, `demo login (${demo.status})`).toBe(true);
  const datasets = (await (await demo.api.get("datasets")).json()) as {
    dataset_id: string;
    dataset_name: string;
  }[];
  const dataset = datasets.find((d) => d.dataset_name === DATASET);
  expect(dataset, `dataset ${DATASET}`).toBeTruthy();
  const generated = await demo.api.post(
    `schedule/generate/${dataset?.dataset_id}`,
    {
      params: { schedule_name: TWO_DAYS, max_days: 2 },
      timeout: 120_000,
    },
  );
  expect(generated.ok(), `generate ${TWO_DAYS}`).toBe(true);
  const twoDays = ((await generated.json()) as Listed).schedule_id;
  const listed = (await (await demo.api.get("schedule")).json()) as Listed[];
  const idOf = (name: string) =>
    listed.find((s) => s.schedule_name === name)?.schedule_id;
  const classic = idOf(CLASSIC);
  const optimized = idOf(OPTIMIZED);
  expect(classic && optimized, "sample schedules").toBeTruthy();

  try {
    await signIn(page);

    await test.step("conflicts tab", async () => {
      await page.goto(
        `/dashboard/${twoDays}?view=conflicts&type=student_double_book`,
      );
      const section = page.locator("section", {
        has: page.getByRole("heading", { name: "Conflict View" }),
      });
      const firstPill = page
        .getByRole("button", { name: /^Open conflict details for / })
        .first();
      await expect(firstPill).toBeVisible();
      await shot(page, section.first(), "conflicts-tab", {
        pad: 8,
        maxHeight: 640,
      });

      const card = cardWith(
        page,
        page.getByRole("group", { name: "Group conflicts" }),
      );
      await card.getByRole("button", { name: "By course" }).click();
      await expect(card.getByText("Students with a conflict")).toBeVisible();
      await shot(page, card, "conflicts-by-course", { maxHeight: 420 });
      await card.getByRole("button", { name: "By student" }).click();

      await firstPill.click();
      const dialog = page.getByRole("dialog");
      await expect(dialog.getByText(/^Student Double-Book: /)).toBeVisible();
      await shot(page, dialog, "conflicts-course-dialog");
      await page.keyboard.press("Escape");
      await expect(dialog).toBeHidden();

      const legend = page.locator("div", {
        has: page.getByRole("heading", { name: "Conflict Definitions" }),
      });
      await shot(page, legend.last(), "conflicts-definitions");
    });

    await test.step("person popup and Open in Explore", async () => {
      await page
        .getByRole("button", { name: /^View exams for NUId / })
        .first()
        .click();
      const popup = page.getByRole("dialog", { name: /^Exams for NUId / });
      await expect(popup.getByText("Double-booked").first()).toBeVisible();
      await shot(page, popup, "explore-person-popup");

      await popup.getByRole("link", { name: "Open in Explore" }).click();
      await expect(popup).toBeHidden();
      const card = cardWith(
        page,
        page.getByRole("button", { name: "Look up" }),
      );
      await expect(card.getByText("Recent:")).toBeVisible();
      await expect(
        card.getByRole("table", { name: "Exam week" }),
      ).toBeVisible();
      await shot(page, card, "explore-student");
    });

    await test.step("explore a room, an instructor and a course", async () => {
      const explore = (query: string) =>
        page.goto(`/dashboard/${classic}?view=explore&${query}`);
      const results = page.getByRole("region", { name: "Results" });

      await explore("kind=room&q=Room%20001");
      await expect(results.getByText("blocked slot")).toBeVisible();
      const roomCard = cardWith(page, page.getByRole("combobox"));
      await shot(page, roomCard, "explore-room");

      await page
        .getByRole("button", { name: "Instructor", exact: true })
        .click();
      await page.getByRole("combobox", { name: "Instructor" }).click();
      await shot(
        page,
        [
          page.getByRole("combobox", { name: "Instructor" }),
          page.getByRole("listbox"),
        ],
        "explore-instructor-picker",
        { pad: 8 },
      );
      await page.getByRole("option").first().click();
      await expect(results).toBeVisible();
      await shot(
        page,
        cardWith(page, page.getByRole("combobox")),
        "explore-instructor",
      );

      await explore("kind=course&q=CSCI%201000");
      await expect(results.getByText("Course CSCI 1000")).toBeVisible();
      await page.getByRole("button", { name: "List" }).click();
      await expect(results.getByRole("table", { name: "Exams" })).toBeVisible();
      await shot(
        page,
        cardWith(page, page.getByRole("combobox")),
        "explore-course-list",
      );
    });

    await test.step("validate the Classic schedule", async () => {
      await page.goto(`/dashboard/${classic}`);
      await page.getByRole("button", { name: "Validate Schedule" }).click();
      const dialog = page.getByRole("dialog");
      await dialog.getByRole("button", { name: "Run Validation" }).click();
      await expect(dialog.getByText(/\d+ checks · /)).toBeVisible({
        timeout: 60_000,
      });
      const warned = dialog.locator('[data-status="warn"]').first();
      await warned.locator("summary").click();
      await shot(page, dialog, "validate-results");
      await page.keyboard.press("Escape");
      await expect(dialog).toBeHidden();
    });

    await test.step("compare Classic and Optimized", async () => {
      await page.goto(`/dashboard/compare?ids=${classic},${optimized}`);
      const settings = page.getByRole("region", { name: "Settings" });
      await expect(settings).toBeVisible();
      // One shot per part: a shot taller than the window comes out cut off.
      const region = (name: string) => page.getByRole("region", { name });
      await shot(
        page,
        [page.getByTestId("compare-column-A"), region("Publishable?")],
        "compare-top",
        { pad: 8 },
      );
      await shot(page, region("Conflicts"), "compare-conflicts", { pad: 8 });
      await shot(page, region("Calendar shape"), "compare-calendar", {
        pad: 8,
      });
      await shot(page, region("Rooms"), "compare-rooms", { pad: 8 });
      await shot(page, region("Room fill by room size"), "compare-room-size", {
        pad: 8,
      });
    });
  } finally {
    await demo.api.delete(`schedule/${twoDays}`);
    await demo.api.dispose();
  }
});
