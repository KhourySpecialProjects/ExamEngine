/**
 * Shared pieces of the docs screenshot run (see start.screenshots.ts for the
 * prerequisites). Each docs section has its own `<section>.screenshots.ts`;
 * they run after start.screenshots.ts, which signs up the demo account, uploads
 * the sample files and generates the two sample schedules.
 */
import { writeFile } from "node:fs/promises";
import path from "node:path";
import {
  type APIRequestContext,
  expect,
  type Locator,
  type Page,
  request,
} from "@playwright/test";

export const API = process.env.DOCS_API_URL ?? "http://localhost:8100/api";
export const ADMIN = {
  email: process.env.DOCS_ADMIN_EMAIL ?? "theadmin@northeastern.edu",
  password: process.env.DOCS_ADMIN_PASSWORD ?? "admin",
};
export const DEMO = {
  name: "Demo User",
  email: "docs-demo@northeastern.edu",
  password: "Docs-demo-2026!",
};
export const PENDING = {
  name: "Pending Demo",
  email: "docs-pending@northeastern.edu",
  password: "Docs-pending-2026!",
};
export const DATASET = "Sample data";
export const CLASSIC = "Sample schedule (Classic)";
export const OPTIMIZED = "Sample schedule (Optimized)";

export const SAMPLE_DIR = path.join(__dirname, "..", "public", "sample-data");
export const OUT_DIR = path.join(__dirname, "..", "content", "docs", "images");
export const SAMPLE_FILES = [
  "courses",
  "enrollments",
  "rooms",
  "room_blockouts",
  "combined_exams",
  "common_exams",
] as const;

export type Account = typeof DEMO;

/** A logged-in API session (the auth cookie lives in the context). */
export async function apiSession(email: string, password: string) {
  const api = await request.newContext({ baseURL: `${API}/` });
  const res = await api.post("auth/login", {
    form: { username: email, password },
  });
  return { api, ok: res.ok(), status: res.status() };
}

/** Sign up an account if needed; approve it when `approve` is set. */
export async function ensureAccount(
  admin: APIRequestContext,
  account: Account,
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
export async function wipeDemo(api: APIRequestContext) {
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

/** Sign the page in as the demo account through the login form. */
export async function signIn(page: Page, account: Account = DEMO) {
  await page.goto("/login");
  const signIn = page.getByRole("tabpanel", { name: "Sign in" });
  await signIn.locator("#email").fill(account.email);
  await signIn.locator("#password").fill(account.password);
  await signIn.getByRole("button", { name: "Login" }).click();
  await page.waitForURL("**/dashboard");
  await expect(page.locator("#schedule-view")).toBeVisible();
}

/** Open a schedule from the schedules list by its name. */
export async function openSchedule(page: Page, name: string) {
  await page.goto("/dashboard");
  await page.locator("#schedule-view").getByRole("link", { name }).click();
  await page.waitForURL(/\/dashboard\/[0-9a-f-]+/);
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
export async function shot(
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

export const toast = (page: Page, title: string) =>
  page.locator("[data-sonner-toast]", { hasText: title });
