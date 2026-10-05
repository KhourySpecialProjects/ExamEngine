import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import type { ScheduleListItem } from "@/lib/api/schedules";
import { useSchedulesViewStore } from "@/lib/store/schedulesViewStore";
import { ScheduleListView } from "./ScheduleListView";

const schedule = (
  name: string,
  createdAt: string,
  dataset = "Spring",
  deleted = false,
): ScheduleListItem => ({
  schedule_id: name,
  schedule_name: name,
  created_at: createdAt,
  algorithm: "DSATUR",
  parameters: {},
  status: "Completed",
  dataset_id: dataset,
  dataset: {
    name: dataset,
    uploaded_at: "2026-01-01T00:00:00",
    deleted,
    courses: 10,
    students: 100,
    rooms: 5,
  },
  total_exams: 10,
  late_add_count: 0,
  based_on_name: null,
});

/** Schedule names in table order. */
const names = () =>
  within(screen.getByRole("table"))
    .getAllByRole("row")
    .slice(1)
    .map((row) => within(row).getAllByRole("cell")[1].textContent);

const twelve = () =>
  Array.from({ length: 12 }, (_, i) =>
    schedule(
      `S${String(i + 1).padStart(2, "0")}`,
      `2026-02-${10 + i}T09:00:00`,
    ),
  );

const chooseRowsPerPage = (size: string) => {
  // Radix Select calls these DOM APIs, which jsdom lacks.
  Element.prototype.hasPointerCapture ??= () => false;
  Element.prototype.scrollIntoView ??= () => {};
  fireEvent.keyDown(screen.getByRole("combobox", { name: "Rows per page" }), {
    key: "Enter",
  });
  fireEvent.keyDown(screen.getByRole("option", { name: size }), {
    key: "Enter",
  });
};

beforeEach(() => {
  sessionStorage.clear();
  useSchedulesViewStore.setState({ pageSize: 10 });
});

describe("ScheduleListView", () => {
  it("opens newest first", () => {
    render(
      <ScheduleListView
        schedules={[
          schedule("Old", "2026-01-05T09:00:00"),
          schedule("Newest", "2026-03-01T09:00:00"),
          schedule("Middle", "2026-02-01T09:00:00"),
        ]}
      />,
    );

    expect(names()).toEqual(["Newest", "Middle", "Old"]);
  });

  it("pages with first/next controls and shows the chosen rows per page", () => {
    render(<ScheduleListView schedules={twelve()} />);
    expect(names()).toHaveLength(10);

    // Bars above and below the table drive the same page.
    fireEvent.click(screen.getAllByRole("button", { name: "Next page" })[1]);
    expect(names()).toEqual(["S02", "S01"]);
    fireEvent.click(screen.getAllByRole("button", { name: "First page" })[0]);
    expect(names()[0]).toBe("S12");
    fireEvent.click(screen.getAllByRole("button", { name: "Next page" })[0]);

    chooseRowsPerPage("25");
    expect(names()).toHaveLength(12);
    expect(names()[0]).toBe("S12");
  });

  it("restores this session's rows per page on the next visit, ignoring invalid values", async () => {
    const KEY = "schedules-view-storage";
    // A later visit starts from the store's defaults and then restores the
    // saved value. Resetting the store writes the default to storage too, so
    // put the saved value back before restoring.
    const nextVisit = async (saved: string | null) => {
      useSchedulesViewStore.setState({ pageSize: 10 });
      if (saved !== null) sessionStorage.setItem(KEY, saved);
      await useSchedulesViewStore.persist.rehydrate();
    };

    const { unmount } = render(<ScheduleListView schedules={twelve()} />);
    chooseRowsPerPage("25");
    unmount();

    await nextVisit(sessionStorage.getItem(KEY));
    render(<ScheduleListView schedules={twelve()} />);
    expect(names()).toHaveLength(12);

    // A stale or edited page size never applies.
    await nextVisit(JSON.stringify({ state: { pageSize: 0 }, version: 0 }));
    expect(useSchedulesViewStore.getState().pageSize).toBe(10);
  });

  it("sorts by dataset and marks deleted datasets", () => {
    render(
      <ScheduleListView
        schedules={[
          schedule("A", "2026-01-01T09:00:00", "Winter"),
          schedule("B", "2026-01-02T09:00:00", "Autumn", true),
          schedule("C", "2026-01-03T09:00:00", "Spring"),
        ]}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Dataset/ }));

    expect(names()).toEqual(["B", "C", "A"]);
    const autumnRow = within(screen.getByRole("table")).getAllByRole("row")[1];
    expect(within(autumnRow).getByText("Deleted")).toBeTruthy();
  });

  it("searches dataset names and starts again from page 1", () => {
    const schedules = [
      ...twelve(),
      schedule("Fall run", "2026-01-01T09:00:00", "Fall 2026"),
    ];
    render(<ScheduleListView schedules={schedules} />);
    fireEvent.click(screen.getAllByRole("button", { name: "Next page" })[0]);

    fireEvent.change(screen.getByPlaceholderText("Search schedules..."), {
      target: { value: "fall 2026" },
    });

    expect(names()).toEqual(["Fall run"]);
    expect(screen.getAllByText("Page 1 of 1")).toHaveLength(2);
  });

  it("shows Late add with the base's name instead of the algorithm for late-add versions", () => {
    render(
      <ScheduleListView
        schedules={[
          schedule("Base", "2026-01-01T09:00:00"),
          {
            ...schedule("V2", "2026-01-02T09:00:00"),
            algorithm: "Late add",
            late_add_count: 1,
            based_on_name: "Base",
          },
          {
            ...schedule("V3", "2026-01-03T09:00:00"),
            algorithm: "Late add",
            late_add_count: 2,
            based_on_name: null,
          },
        ]}
      />,
    );
    const row = (name: string) =>
      screen.getByRole("link", { name }).closest("tr") as HTMLElement;

    expect(within(row("V2")).getByText("Late add").title).toBe("Based on Base");
    expect(within(row("V3")).getByText("Late add").title).toBe(
      "Based on a schedule that is not available",
    );
    expect(within(row("Base")).getByText("DSATUR")).toBeTruthy();
    expect(within(row("Base")).queryByText("Late add")).toBeNull();
  });
});
