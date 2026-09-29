import { beforeEach, describe, expect, it, vi } from "vitest";
import { DatasetsAPI } from "@/lib/api/datasets";

vi.mock("@/lib/api/client", () => ({
  apiClient: { datasets: { upload: vi.fn() } },
}));

import { apiClient } from "@/lib/api/client";
import { useUploadStore } from "./uploadStore";

const upload = vi.mocked(apiClient.datasets.upload);
const csv = (name: string) => new File(["a,b\n1,2\n"], name);

function selectFiles(ids: string[]) {
  const store = useUploadStore.getState();
  store.reset();
  store.setDatasetName("Test dataset");
  for (const id of ids) store.setFile(id, csv(`${id}.csv`));
}

const slot = (id: string) =>
  useUploadStore.getState().slots.find((s) => s.id === id)?.file;

describe("uploadAll failure", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("moves every uploading slot to error, with per-file validation messages", async () => {
    selectFiles(["courses", "enrollments", "rooms"]);
    upload.mockRejectedValue(
      new Error(
        JSON.stringify({
          message: "File validation failed",
          errors: { rooms: "Missing columns: Location Name, Capacity" },
        }),
      ),
    );

    await expect(useUploadStore.getState().uploadAll()).rejects.toThrow();

    expect(slot("rooms")).toMatchObject({
      status: "error",
      error: "Missing columns: Location Name, Capacity",
    });
    for (const id of ["courses", "enrollments"]) {
      expect(slot(id)).toMatchObject({
        status: "error",
        error: "Not uploaded: another file failed validation",
      });
    }
    expect(useUploadStore.getState().isUploading).toBe(false);
  });

  it("uses the plain message when the error is not a validation payload", async () => {
    selectFiles(["courses", "enrollments", "rooms"]);
    upload.mockRejectedValue(new Error("Network down"));

    await expect(useUploadStore.getState().uploadAll()).rejects.toThrow();

    expect(slot("rooms")).toMatchObject({
      status: "error",
      error: "Network down",
    });
  });
});

describe("API errors with an object detail", () => {
  it("surface the detail as parseable JSON, not [object Object]", async () => {
    const detail = {
      message: "File validation failed",
      errors: { rooms: "Missing columns: Location Name, Capacity" },
    };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 400,
        statusText: "Bad Request",
        json: async () => ({ detail }),
      }),
    );

    const api = new DatasetsAPI("http://api.test");
    const error = await api
      .upload("x", {
        courses: csv("c.csv"),
        enrollments: csv("e.csv"),
        rooms: csv("r.csv"),
      })
      .catch((e: Error) => e);

    expect(JSON.parse((error as Error).message)).toEqual(detail);
    vi.unstubAllGlobals();
  });
});
