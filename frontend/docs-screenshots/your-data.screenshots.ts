/**
 * Screenshots for the Your data section (content/docs/your-data). Runs after
 * start.screenshots.ts; see that file for prerequisites. Uploads the sample
 * files a second time as COPY (the success and warning messages), then tries
 * them again under BROKEN with a rooms file missing its capacity column (the
 * failed upload, which saves nothing). COPY is then deleted through the
 * sidebar, for the delete confirmation.
 */
import path from "node:path";
import { expect, test } from "@playwright/test";
import { SAMPLE_DIR, SAMPLE_FILES, shot, signIn, toast } from "./support";

const COPY = "Sample data (copy)";
const BROKEN = "Sample data (broken)";

// A rooms file without a capacity column: rejected for missing columns.
const BROKEN_ROOMS = {
  name: "rooms.csv",
  mimeType: "text/csv",
  buffer: Buffer.from("Room,Size\nRoom 001,31\nRoom 002,53\n"),
};

test("your data screenshots", async ({ page }) => {
  // Tall enough for the whole Upload dialog, including the message under its
  // buttons, without scrolling.
  await page.setViewportSize({ width: 1440, height: 1500 });
  await signIn(page);
  const sidebar = page.locator("#control-center");

  await test.step("a successful upload, then a failed one", async () => {
    await page.locator("#upload-id").click();
    const dialog = page.getByRole("dialog", { name: "Upload Dataset" });
    const inputs = dialog.locator('input[type="file"]');
    const uploadAll = dialog.getByRole("button", { name: "Upload All Files" });
    const addFiles = async (
      name: string,
      rooms: typeof BROKEN_ROOMS | null,
    ) => {
      await dialog.locator("#dataset-name").fill(name);
      for (const [i, file] of SAMPLE_FILES.entries()) {
        await inputs
          .nth(i)
          .setInputFiles(
            file === "rooms" && rooms
              ? rooms
              : path.join(SAMPLE_DIR, `${file}.csv`),
          );
      }
    };

    await addFiles(COPY, null);
    await uploadAll.click();
    await expect(toast(page, "Upload successful!")).toBeVisible();
    const warning = toast(page, "Some combined exams exceed room capacity");
    await expect(warning).toBeVisible();
    await shot(page, warning, "upload-warning", { toasts: true });
    await expect(
      dialog.getByText("All files uploaded successfully!"),
    ).toBeVisible();
    await shot(page, dialog, "upload-success");

    // Reopen the dialog: its file inputs still hold the files just uploaded,
    // and choosing the same file again fires no change event.
    await dialog.getByRole("button", { name: "Clear All" }).click();
    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();
    await page.locator("#upload-id").click();
    await addFiles(BROKEN, BROKEN_ROOMS);
    await uploadAll.click();
    await expect(toast(page, "Validation failed")).toBeVisible();
    await expect(
      dialog.getByText("Some files failed to upload. Please try again."),
    ).toBeVisible();
    await shot(page, dialog, "upload-failed");
    await dialog.getByRole("button", { name: "Clear All" }).click();
    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();
  });

  await test.step("the Current Dataset panel and the picker", async () => {
    const picker = sidebar.getByRole("combobox").filter({ hasText: COPY });
    // The block holding the heading, the counts and the warnings.
    const panel = sidebar
      .getByText("Current Dataset", { exact: true })
      .locator("..");
    await expect(panel.getByText("will be unscheduled")).toBeVisible();
    await shot(page, panel, "current-dataset", { pad: 8 });

    await picker.click();
    const popover = page.locator('[data-slot="popover-content"]');
    await expect(popover.getByRole("option", { name: COPY })).toBeVisible();
    await shot(page, [picker, popover], "dataset-picker", { pad: 8 });
    await page.keyboard.press("Escape");
    await expect(popover).toBeHidden();
  });

  await test.step("delete the copy", async () => {
    await sidebar.locator("button:has(svg.lucide-trash)").click();
    const confirm = page.getByRole("alertdialog", {
      name: "Are you absolutely sure?",
    });
    await expect(confirm.getByText(COPY)).toBeVisible();
    await shot(page, confirm, "delete-dataset");
    await confirm.getByRole("button", { name: "Continue" }).click();
    await expect(
      sidebar.getByRole("combobox").filter({ hasText: "Choose Dataset" }),
    ).toBeVisible();
  });
});
