import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import {
  NuqsTestingAdapter,
  type OnUrlUpdateFunction,
} from "nuqs/adapters/testing";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { apiClient } from "@/lib/api/client";
import type {
  ComparedSchedule,
  CompareItem,
  ScheduleSummary,
} from "@/lib/api/schedules";
import { makeSummary } from "@/test/summary";
import { ComparePage } from "./ComparePage";

// recharts' ResponsiveContainer needs it; jsdom has none.
beforeAll(() => {
  global.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
});

const A = "0b6f1c1e-0000-4000-8000-00000000000a";
const B = "0b6f1c1e-0000-4000-8000-00000000000b";
const GONE = "0b6f1c1e-0000-4000-8000-0000000000ff";

const base = makeSummary();

function compared(
  id: string,
  name: string,
  summary: ScheduleSummary = base,
): ComparedSchedule {
  return {
    schedule_id: id,
    status: "ok",
    schedule_name: name,
    created_at: "2026-01-01T00:00:00",
    run_status: "Completed",
    dataset: {
      dataset_id: "d1",
      dataset_name: "Spring",
      uploaded_at: "2026-01-01T00:00:00",
      deleted: false,
    },
    summary,
    is_owner: true,
    is_shared: false,
    created_by_user_id: "u1",
    created_by_user_name: "Me",
    shared_by_user_id: null,
    shared_by_user_name: null,
  };
}

const PLAN_A = compared(A, "Plan A", {
  ...base,
  conflicts: {
    ...base.conflicts,
    student_double_book: { people: 5, instances: 7 },
  },
});
const PLAN_B = compared(B, "Plan B", {
  ...base,
  conflicts: {
    ...base.conflicts,
    student_double_book: { people: 3, instances: 3 },
  },
});

/** Answers like the server: requested order, unknown ids unavailable. */
function serve(...known: ComparedSchedule[]) {
  return vi
    .spyOn(apiClient.schedules, "compare")
    .mockImplementation(async (ids) => ({
      schedules: ids.map(
        (id): CompareItem =>
          known.find((s) => s.schedule_id === id) ?? {
            schedule_id: id,
            status: "unavailable",
          },
      ),
    }));
}

function renderPage(search: string) {
  const onUrlUpdate = vi.fn<OnUrlUpdateFunction>();
  render(
    <NuqsTestingAdapter
      searchParams={search}
      onUrlUpdate={onUrlUpdate}
      hasMemory
    >
      <ComparePage />
    </NuqsTestingAdapter>,
  );
  const lastUrl = () => onUrlUpdate.mock.lastCall?.[0].searchParams;
  const lastHistory = () => onUrlUpdate.mock.lastCall?.[0].options.history;
  return { lastUrl, lastHistory };
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("ComparePage", () => {
  it("loads every column in one request; unknown and mangled ids get a neutral column", async () => {
    const compare = serve(PLAN_A, PLAN_B);

    renderPage(`?ids=${A},${GONE},${B},not-an-id`);

    expect(await screen.findByText("Plan A")).toBeTruthy();
    expect(screen.getByText("Plan B")).toBeTruthy();
    expect(screen.getAllByText("Not available")).toHaveLength(2);
    // The mangled id never reaches the server (it would reject the request).
    expect(compare).toHaveBeenCalledTimes(1);
    expect(compare).toHaveBeenCalledWith([A, GONE, B]);
    // Plan A is the baseline: Plan B has 2 fewer double-booked students.
    expect(screen.getByTitle("better than the baseline").textContent).toContain(
      "−2",
    );
  });

  it("moves a new baseline to the front with its colour, then drops other columns without refetching", async () => {
    const compare = serve(PLAN_A, PLAN_B);
    const { lastUrl } = renderPage(`?ids=${A},${GONE},${B}`);
    await screen.findByText("Plan A");

    fireEvent.keyDown(
      screen.getByRole("button", { name: "Column C options" }),
      { key: "Enter" },
    );
    // Column C has the third colour (the unavailable column holds the second).
    const green = "rgb(0, 158, 115)";
    expect(screen.getByTestId("compare-column-C").style.borderTopColor).toBe(
      green,
    );
    fireEvent.click(await screen.findByText("Set as baseline"));

    await waitFor(() =>
      expect(lastUrl()?.get("ids")).toBe(`${B},${A},${GONE}`),
    );
    const first = screen.getByTestId("compare-column-A");
    expect(within(first).getByText("Plan B")).toBeTruthy();
    expect(first.style.borderTopColor).toBe(green);
    expect(screen.getByTitle("worse than the baseline").textContent).toContain(
      "+2",
    );

    fireEvent.click(screen.getByRole("button", { name: "Remove" }));

    await waitFor(() => expect(lastUrl()?.get("ids")).toBe(`${B},${A}`));
    expect(compare).toHaveBeenCalledTimes(1);
  });

  it("shows the first available schedule first; removing it makes the next one the baseline", async () => {
    serve(PLAN_A, PLAN_B);
    const { lastUrl } = renderPage(`?ids=${GONE},${B},${A}`);
    await screen.findByText("Plan A");

    const first = screen.getByTestId("compare-column-A");
    expect(within(first).getByText("Plan B")).toBeTruthy();
    expect(within(first).getByText("Baseline")).toBeTruthy();

    fireEvent.keyDown(
      screen.getByRole("button", { name: "Column A options" }),
      { key: "Enter" },
    );
    const remove = await screen.findByRole("menuitem", { name: "Remove" });
    expect(screen.queryByRole("menuitem", { name: "Move left" })).toBeNull();
    fireEvent.click(remove);

    await waitFor(() => expect(lastUrl()?.get("ids")).toBe(`${GONE},${A}`));
  });

  it("turns an old base= link into the first column, replacing the history entry", async () => {
    serve(PLAN_A, PLAN_B);
    const { lastUrl, lastHistory } = renderPage(`?ids=${A},${B}&base=${B}`);

    await waitFor(() => expect(lastUrl()?.get("ids")).toBe(`${B},${A}`));
    expect(lastUrl()?.has("base")).toBe(false);
    expect(lastHistory()).toBe("replace");
    expect(
      within(await screen.findByTestId("compare-column-A")).getByText("Plan B"),
    ).toBeTruthy();
  });

  it("never moves a column left onto the baseline from the menu", async () => {
    serve(PLAN_A, PLAN_B);
    renderPage(`?ids=${A},${B}`);
    await screen.findByText("Plan A");

    fireEvent.keyDown(
      screen.getByRole("button", { name: "Column B options" }),
      { key: "Enter" },
    );
    const left = await screen.findByRole("menuitem", { name: "Move left" });
    expect(left.getAttribute("aria-disabled")).toBe("true");
  });

  it("names the schedule left when fewer than two can be shown", async () => {
    serve(PLAN_A);

    renderPage(`?ids=${A},${GONE}`);

    expect(
      await screen.findByText("Add a schedule to compare with Plan A"),
    ).toBeTruthy();
    expect(screen.getByText(/1 linked schedule is not available/)).toBeTruthy();
  });

  it("links each schedule, and each conflict count above zero to that type of conflict, in a new tab", async () => {
    serve(PLAN_A, PLAN_B);
    renderPage(`?ids=${A},${B}`);
    await screen.findByText("Plan A");

    const view = screen.getByRole("link", {
      name: "View schedule Plan B (opens in a new tab)",
    });
    expect(view.getAttribute("href")).toBe(`/dashboard/${B}`);
    expect(view.getAttribute("target")).toBe("_blank");

    const cell = screen.getByRole("link", {
      name: "3 students: Student Double-Book in Plan B (opens in a new tab)",
    });
    expect(cell.getAttribute("href")).toBe(
      `/dashboard/${B}?view=conflicts&type=student_double_book`,
    );
    expect(cell.getAttribute("target")).toBe("_blank");
    // A zero count has nothing to list.
    expect(
      screen.queryByRole("link", { name: /Instructor Double-Book/ }),
    ).toBeNull();
  });
});
