/**
 * Screenshots for the user docs (content/docs), taken from the running app with
 * the synthetic sample files in public/sample-data. Re-run after UI changes:
 *
 *   cd frontend && npm run docs:screenshots
 *
 * Prerequisites:
 * - The local dev stack is up (`docker compose --profile dev up -d`): the app at
 *   DOCS_BASE_URL (default http://localhost:3000) and its API at DOCS_API_URL
 *   (default http://localhost:8100/api).
 * - The seeded admin account (DOCS_ADMIN_EMAIL / DOCS_ADMIN_PASSWORD, defaults =
 *   the backend's dev seed), used only to approve the demo account.
 * - Chromium for Playwright (`npx playwright install chromium`, once).
 *
 * The script creates two accounts if they are missing: docs-demo@ (approved; the
 * one in the screenshots) and docs-pending@ (never approved, for the "pending"
 * message). The demo account is reserved for this script: its datasets and
 * schedules are deleted at the start and the end of every run.
 *
 * Images are written as WebP to content/docs/images/<name>.webp.
 */
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import {
  type APIRequestContext,
  expect,
  type Locator,
  type Page,
  request,
  test,
} from "@playwright/test";

const API = process.env.DOCS_API_URL ?? "http://localhost:8100/api";
const ADMIN = {
  email: process.env.DOCS_ADMIN_EMAIL ?? "theadmin@northeastern.edu",
  password: process.env.DOCS_ADMIN_PASSWORD ?? "admin",
};
const DEMO = {
  name: "Demo User",
  email: "docs-demo@northeastern.edu",
  password: "Docs-demo-2026!",
};
const PENDING = {
  name: "Pending Demo",
  email: "docs-pending@northeastern.edu",
  password: "Docs-pending-2026!",
};
const DATASET = "Sample data";
const CLASSIC = "Sample schedule (Classic)";
const OPTIMIZED = "Sample schedule (Optimized)";

const SAMPLE_DIR = path.join(__dirname, "..", "public", "sample-data");
const OUT_DIR = path.join(__dirname, "..", "content", "docs", "images");
const SAMPLE_FILES = [
  "courses",
  "enrollments",
  "rooms",
  "room_blockouts",
  "combined_exams",
  "common_exams",
] as const;

/** A logged-in API session (the auth cookie lives in the context). */
async function apiSession(email: string, password: string) {
  const api = await request.newContext({ baseURL: `${API}/` });
  const res = await api.post("auth/login", {
    form: { username: email, password },
  });
  return { api, ok: res.ok(), status: res.status() };
}

/** Sign up an account if needed; approve it when `approve` is set. */
async function ensureAccount(
  admin: APIRequestContext,
  account: typeof DEMO,
  approve: boolean,
) {
  const anon = await request.newContext({ baseURL: `${API}/` });
  const res = await anon.post("auth/signup", {
    data: {
      name: account.name,
      email: account.email,
      password: account.password,
    },
  });
  // 400 = already registered: fine, the account exists from an earlier run.
  if (!res.ok() && res.status() !== 400) {
    throw new Error(
      `signup ${account.email}: ${res.status()} ${await res.text()}`,
    );
  }
  await anon.dispose();
  if (!approve) return;
  const pending = await (await admin.get("admin/users/pending")).json();
  const user = (pending as { email: string; user_id: string }[]).find(
    (u) => u.email === account.email,
  );
  if (user) {
    const ok = await admin.post(`admin/users/${user.user_id}/approve`);
    expect(ok.ok(), `approve ${account.email}`).toBe(true);
  }
}

/** Delete every schedule and dataset the demo account owns. */
async function wipeDemo(api: APIRequestContext) {
  const schedules = await (await api.get("schedule")).json();
  for (const s of schedules as { schedule_id: string; is_owner?: boolean }[]) {
    if (s.is_owner === false) continue;
    await api.delete(`schedule/${s.schedule_id}`);
  }
  const datasets = await (await api.get("datasets")).json();
  for (const d of datasets as { dataset_id: string }[]) {
    await api.delete(`datasets/${d.dataset_id}`);
  }
}

type ShotOptions = {
  /** CSS pixels of surrounding page to include. */
  pad?: number;
  /** Crop to this many CSS pixels from the top. */
  maxHeight?: number;
  /** Keep toasts visible (they are hidden by default, as they cover things). */
  toasts?: boolean;
};

/**
 * Save an element, or the smallest area holding several, as
 * content/docs/images/<name>.webp.
 */
async function shot(
  page: Page,
  target: Locator | Locator[],
  name: string,
  { pad = 0, maxHeight = Infinity, toasts = false }: ShotOptions = {},
) {
  const targets = Array.isArray(target) ? target : [target];
  await targets[0].scrollIntoViewIfNeeded();
  const boxes = [];
  for (const t of targets) {
    const box = await t.boundingBox();
    if (!box) throw new Error(`${name}: element not visible`);
    boxes.push(box);
  }
  const left = Math.min(...boxes.map((b) => b.x));
  const top = Math.min(...boxes.map((b) => b.y));
  const right = Math.max(...boxes.map((b) => b.x + b.width));
  const bottom = Math.max(...boxes.map((b) => b.y + b.height));
  const scroll = await page.evaluate(() => ({ x: scrollX, y: scrollY }));
  // Let entrance animations (dialogs, toasts, popovers) settle.
  await page.waitForTimeout(500);
  const png = await page.screenshot({
    fullPage: true,
    clip: {
      x: Math.max(0, left + scroll.x - pad),
      y: Math.max(0, top + scroll.y - pad),
      width: right - left + 2 * pad,
      height: Math.min(bottom - top, maxHeight) + 2 * pad,
    },
    // The Next dev-tools badge (nextjs-portal) never belongs in the docs.
    style: `nextjs-portal { display: none !important; }${
      toasts ? "" : " [data-sonner-toaster] { visibility: hidden !important; }"
    }`,
  });
  // Playwright writes PNG or JPEG only; the browser re-encodes it as WebP.
  const webp = await page.evaluate(async (base64) => {
    const img = new Image();
    img.src = `data:image/png;base64,${base64}`;
    await img.decode();
    const canvas = document.createElement("canvas");
    canvas.width = img.naturalWidth;
    canvas.height = img.naturalHeight;
    canvas.getContext("2d")?.drawImage(img, 0, 0);
    return canvas.toDataURL("image/webp", 0.9).split(",")[1];
  }, png.toString("base64"));
  await writeFile(
    path.join(OUT_DIR, `${name}.webp`),
    Buffer.from(webp, "base64"),
  );
}

const toast = (page: Page, title: string) =>
  page.locator("[data-sonner-toast]", { hasText: title });

// The `page` fixture carries the config's viewport and scale, and starts with
// no cookies (the login page redirects signed-in users).
test("docs screenshots", async ({ page }) => {
  await mkdir(OUT_DIR, { recursive: true });

  const admin = await apiSession(ADMIN.email, ADMIN.password);
  expect(admin.ok, `admin login (${admin.status}); set DOCS_ADMIN_*`).toBe(
    true,
  );
  await ensureAccount(admin.api, DEMO, true);
  await ensureAccount(admin.api, PENDING, false);
  const demo = await apiSession(DEMO.email, DEMO.password);
  expect(demo.ok, `demo login (${demo.status})`).toBe(true);
  await wipeDemo(demo.api);

  await test.step("sign up and sign in", async () => {
    await page.goto("/login#signup");
    const signUp = page.getByRole("tabpanel", { name: "Sign up" });
    await signUp.locator("#su-name").fill(DEMO.name);
    await signUp.locator("#su-email").fill(DEMO.email);
    await signUp.locator("#su-password").fill(DEMO.password);
    await signUp.locator("#su-password").blur();
    await shot(page, signUp, "signup");

    await page.getByRole("tab", { name: "Sign in" }).click();
    const signIn = page.getByRole("tabpanel", { name: "Sign in" });
    await signIn.locator("#email").fill(PENDING.email);
    await signIn.locator("#password").fill(PENDING.password);
    await signIn.getByRole("button", { name: "Login" }).click();
    await shot(
      page,
      toast(page, "Account Pending Approval"),
      "pending-approval",
      { toasts: true },
    );

    await signIn.locator("#email").fill(DEMO.email);
    await signIn.locator("#password").fill(DEMO.password);
    await signIn.locator("#password").blur();
    await shot(page, signIn, "signin");
    await signIn.getByRole("button", { name: "Login" }).click();
    await page.waitForURL("**/dashboard");
    await expect(page.locator("#schedule-view")).toBeVisible();
  });

  await test.step("upload the sample files", async () => {
    await page.locator("#upload-id").click();
    const dialog = page.getByRole("dialog", { name: "Upload Dataset" });
    await dialog.locator("#dataset-name").fill(DATASET);
    const inputs = dialog.locator('input[type="file"]');
    for (const [i, file] of SAMPLE_FILES.entries()) {
      await inputs.nth(i).setInputFiles(path.join(SAMPLE_DIR, `${file}.csv`));
    }
    await shot(page, dialog, "upload-dialog");
    await dialog.getByRole("button", { name: "Upload All Files" }).click();
    await expect(toast(page, "Upload successful!")).toBeVisible();
    await expect(
      dialog.getByText("All files uploaded successfully!"),
    ).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();

    // The sidebar with the new dataset selected, cropped below its controls.
    const sidebar = page.locator("#control-center");
    await expect(sidebar.getByText("Current Dataset")).toBeVisible();
    const top = (await sidebar.boundingBox())?.y ?? 0;
    const generate = await page.locator("#generate-id").boundingBox();
    const maxHeight = (generate ? generate.y + generate.height : 0) - top + 24;
    await shot(page, sidebar, "controls-center", { maxHeight });
  });

  await test.step("generate Classic and Optimized schedules", async () => {
    await page.locator("#generate-id").click();
    const dialog = page.getByRole("dialog", { name: "Optimize Exam Schedule" });
    await dialog.locator("#schedule-name").fill(CLASSIC);
    await shot(page, dialog, "generate-dialog");
    await dialog.getByRole("button", { name: "Generate Schedule" }).click();
    const generated = toast(page, "Schedule generated!");
    await expect(generated).toBeVisible({ timeout: 120_000 });
    // Wait for that toast to go, so the next one can be told apart.
    await expect(generated).toHaveCount(0, { timeout: 30_000 });

    await dialog
      .getByRole("group", { name: "Algorithm" })
      .getByRole("button", { name: "Optimized" })
      .click();
    await dialog.locator("#schedule-name").fill(OPTIMIZED);
    await dialog.getByRole("button", { name: "Generate Schedule" }).click();
    await expect(generated).toBeVisible({ timeout: 120_000 });
    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();
  });

  await test.step("header, user menu and tour", async () => {
    const header = page.locator("header").first();
    await shot(page, header, "header");

    // Not by role: while the menu is open, Radix hides the rest from ARIA.
    const userButton = header.locator("button", { hasText: DEMO.name });
    await userButton.click();
    const menu = page.getByRole("menu");
    const headerRight = header.locator(":scope > div").last();
    await shot(page, [headerRight, menu], "user-menu", { pad: 8 });
    await page.keyboard.press("Escape");
    await expect(menu).toBeHidden();

    await header.locator("button:has(svg.lucide-circle-question-mark)").click();
    const card = page
      .locator('[data-slot="card"]')
      .filter({ hasText: "1 of 5" });
    await expect(card).toBeVisible();
    // The highlighted sidebar and the tour card, cropped below the card.
    const sidebar = page.locator("#control-center");
    const sidebarTop = (await sidebar.boundingBox())?.y ?? 0;
    const cardBox = await card.boundingBox();
    await shot(page, [sidebar, card], "tour", {
      maxHeight: (cardBox ? cardBox.y + cardBox.height : 0) - sidebarTop + 16,
    });
    await card.locator("button:has(svg.lucide-x)").click();
    await expect(card).toBeHidden();
  });

  await test.step("review the Classic schedule", async () => {
    const list = page.locator("#schedule-view");
    await expect(list.getByRole("link", { name: OPTIMIZED })).toBeVisible();
    await expect(list.getByText("Running")).toHaveCount(0);
    await shot(page, list, "schedules-list");

    await list.getByRole("link", { name: CLASSIC }).click();
    await page.waitForURL(/\/dashboard\/[0-9a-f-]+/);
    await page.getByRole("tab", { name: "Statistics" }).click();
    const problems = page.locator('section[aria-labelledby="stats-problems"]');
    await expect(problems).toBeVisible();
    await shot(page, problems, "statistics-needs-attention", { pad: 8 });

    await page.getByRole("tab", { name: "Conflicts" }).click();
    const conflicts = page.locator("section", {
      has: page.getByRole("heading", { name: "Conflict View" }),
    });
    await expect(
      conflicts.getByRole("group", { name: "Conflict types" }),
    ).toBeVisible();
    await shot(page, conflicts.first(), "conflicts", {
      pad: 8,
      maxHeight: 760,
    });

    // The innermost row holding both the view tabs and the action buttons.
    const toolbar = page
      .locator("div")
      .filter({ has: page.getByRole("tablist") })
      .filter({ has: page.getByRole("button", { name: "Export Schedule" }) })
      .last();
    await shot(page, toolbar, "schedule-toolbar", { pad: 8 });
    const download = page.waitForEvent("download");
    await page.getByRole("button", { name: "Export Schedule" }).click();
    expect((await download).suggestedFilename()).toBe("schedule_exams.csv");
  });

  await test.step("change password form", async () => {
    await page.goto("/dashboard/settings");
    const card = page
      .locator('[data-slot="card"]')
      .filter({ has: page.getByText("Change Password", { exact: true }) });
    await shot(page, card, "change-password");
  });

  await wipeDemo(demo.api);
  await demo.api.dispose();
  await admin.api.dispose();
});
