import { afterEach, describe, expect, it, vi } from "vitest";
import { SchedulesAPI } from "./schedules";

function stubFetch() {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({}),
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("SchedulesAPI.generate query string", () => {
  it("includes algorithm and time budget when set", async () => {
    vi.spyOn(console, "log").mockImplementation(() => {});
    const fetchMock = stubFetch();

    await new SchedulesAPI("http://api.test").generate("ds1", "Finals", {
      algorithm: "annealing",
      time_budget_seconds: 30,
    });

    expect(fetchMock.mock.calls[0][0]).toContain(
      "algorithm=annealing&time_budget_seconds=30",
    );
  });

  it("omits algorithm and time budget when undefined", async () => {
    vi.spyOn(console, "log").mockImplementation(() => {});
    const fetchMock = stubFetch();

    await new SchedulesAPI("http://api.test").generate("ds1", "Finals", {});

    const url = fetchMock.mock.calls[0][0] as string;
    expect(url).not.toContain("algorithm");
    expect(url).not.toContain("time_budget_seconds");
  });
});
