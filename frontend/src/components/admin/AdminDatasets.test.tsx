import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { AdminDataset } from "@/lib/api/admin";
import type * as utils from "@/lib/utils";
import { AdminDatasets } from "./AdminDatasets";

vi.mock("sonner", () => ({
  toast: { error: vi.fn() },
}));

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    admin: { getAllDatasets: vi.fn(), downloadDataset: vi.fn() },
  },
}));

vi.mock("@/lib/utils", async (importOriginal) => ({
  ...(await importOriginal<typeof utils>()),
  downloadBlob: vi.fn(),
}));

import { apiClient } from "@/lib/api/client";

const getAllDatasets = vi.mocked(apiClient.admin.getAllDatasets);
const downloadDataset = vi.mocked(apiClient.admin.downloadDataset);

function dataset(id: string, name: string): AdminDataset {
  return {
    dataset_id: id,
    dataset_name: name,
    created_at: "2026-09-30T17:57:38",
    owner_name: "Administrator",
    owner_email: "admin@northeastern.edu",
    file_types: ["courses", "enrollments", "rooms"],
  };
}

describe("AdminDatasets", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("reports a failed load instead of an empty dataset list", async () => {
    getAllDatasets.mockRejectedValue(new Error("Admin access required"));

    render(<AdminDatasets />);

    expect(
      await screen.findByText("Failed to load datasets: Admin access required"),
    ).toBeTruthy();
    expect(screen.queryByText("No datasets")).toBeNull();
  });

  it("keeps every download disabled until the active download finishes", async () => {
    getAllDatasets.mockResolvedValue([
      dataset("a", "Fall 2026"),
      dataset("b", "Spring 2027"),
    ]);
    const download = Promise.withResolvers<Blob>();
    downloadDataset.mockReturnValue(download.promise);

    render(<AdminDatasets />);
    const [first, second] = await screen.findAllByRole("button", {
      name: "Download",
    });
    fireEvent.click(first);

    await waitFor(() => {
      expect(first.hasAttribute("disabled")).toBe(true);
      expect(second.hasAttribute("disabled")).toBe(true);
    });
    fireEvent.click(second);
    expect(downloadDataset).toHaveBeenCalledTimes(1);

    download.resolve(new Blob(["PK"]));
    await waitFor(() => expect(second.hasAttribute("disabled")).toBe(false));
  });
});
