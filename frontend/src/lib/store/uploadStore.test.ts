import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DatasetsAPI } from "@/lib/api/datasets";

vi.mock("@/lib/api/client", () => ({
  apiClient: { datasets: { upload: vi.fn() } },
}));

import { apiClient } from "@/lib/api/client";
import { useUploadStore } from "./uploadStore";

const upload = vi.mocked(apiClient.datasets.upload);
const csv = (name: string) => new File(["a,b\n1,2\n"], name);

// Restore stubbed globals (fetch) even when an assertion fails mid-test.
afterEach(() => {
  vi.unstubAllGlobals();
});

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

describe("uploadAll success with optional exam-group files", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("sends combined and common files under separate keys and marks both slots", async () => {
    selectFiles([
      "courses",
      "enrollments",
      "rooms",
      "combined_exams",
      "common_exams",
    ]);
    upload.mockResolvedValue({
      dataset_id: "d1",
      dataset_name: "Test dataset",
      created_at: "",
      status: "ok",
      files: {
        courses: { rows: 1 },
        enrollments: { rows: 1 },
        rooms: { rows: 1 },
        combined_exams: { rows: 4 },
        common_exams: { rows: 7 },
      },
    } as never);

    await useUploadStore.getState().uploadAll();

    const files = upload.mock.calls[0][1];
    expect(files.combined_exams?.name).toBe("combined_exams.csv");
    expect(files.common_exams?.name).toBe("common_exams.csv");
    expect(slot("combined_exams")).toMatchObject({
      status: "success",
      rowCount: 4,
    });
    expect(slot("common_exams")).toMatchObject({
      status: "success",
      rowCount: 7,
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
  });
});

describe("DatasetsAPI.upload form fields", () => {
  it("posts combined and common exam files under their own field names", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({}),
    });
    vi.stubGlobal("fetch", fetchMock);

    await new DatasetsAPI("http://api.test").upload("x", {
      courses: csv("c.csv"),
      enrollments: csv("e.csv"),
      rooms: csv("r.csv"),
      combined_exams: csv("combined.csv"),
      common_exams: csv("common.csv"),
    });

    const body = fetchMock.mock.calls[0][1].body as FormData;
    expect((body.get("combined_exams") as File).name).toBe("combined.csv");
    expect((body.get("common_exams") as File).name).toBe("common.csv");
  });
});
