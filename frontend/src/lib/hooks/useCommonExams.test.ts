import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/client", () => ({
  apiClient: { datasets: { getCommonExams: vi.fn() } },
}));

import { apiClient } from "@/lib/api/client";
import { useCommonExams } from "./useCommonExams";

const getCommonExams = vi.mocked(apiClient.datasets.getCommonExams);

describe("useCommonExams", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("pulls every member of a combined exam into the common group it touches", async () => {
    getCommonExams.mockResolvedValue({ BIOL101: ["11111", "33333"] });
    const merges = { combo: ["11111", "22222"], other: ["55555", "66666"] };

    const { result } = renderHook(() => useCommonExams("d1", merges));

    await waitFor(() =>
      expect(result.current.commonGroups).toEqual({
        BIOL101: ["11111", "33333"],
      }),
    );
    expect(result.current.isCommon("11111")).toBe(true);
    expect(result.current.isCommon("22222")).toBe(true);
    expect(result.current.isCommon(" 33333 ")).toBe(true);
    expect(result.current.isCommon("55555")).toBe(false);
    expect(result.current.isCommon("")).toBe(false);
  });

  it("reports nothing as common when loading fails", async () => {
    getCommonExams.mockRejectedValue(new Error("boom"));

    const { result } = renderHook(() => useCommonExams("d1"));

    await waitFor(() => expect(result.current.error).toBe("boom"));
    expect(result.current.isCommon("11111")).toBe(false);
  });
});
