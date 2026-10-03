import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import type { ScheduleListItem } from "@/lib/api/schedules";
import { useSchedulesViewStore } from "@/lib/store/schedulesViewStore";
import { ScheduleGroupsView } from "./ScheduleGroupsView";

const schedule = (
  name: string,
  createdAt: string,
  dataset: string,
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
    deleted: dataset === "Old",
    courses: 120,
    students: 3400,
    rooms: 18,
  },
  total_exams: 10,
});

const SCHEDULES = [
  schedule("Spring A", "2026-03-01T09:00:00", "Spring"),
  schedule("Old A", "2025-01-01T09:00:00", "Old"),
  schedule("Autumn A", "2026-04-01T09:00:00", "Autumn"),
  schedule("Autumn B", "2026-02-01T09:00:00", "Autumn"),
];

/** Dataset names in order, with whether each group is expanded. */
const groups = () =>
  screen.getAllByRole("region").map((section) => {
    const toggle = within(section).getAllByRole("button")[0];
    return [
      section.getAttribute("aria-label"),
      toggle.getAttribute("aria-expanded"),
    ];
  });

beforeEach(() => {
  sessionStorage.clear();
  useSchedulesViewStore.setState({ datasetPageSize: 10 });
});

describe("ScheduleGroupsView", () => {
  it("lists datasets by latest run with only the most recent expanded", () => {
    render(<ScheduleGroupsView schedules={SCHEDULES} />);

    expect(groups()).toEqual([
      ["Autumn", "true"],
      ["Spring", "false"],
      ["Old", "false"],
    ]);
    const autumn = screen.getByRole("region", { name: "Autumn" });
    expect(
      within(autumn).getByText(/120 courses · 3,400 students · 18 rooms/),
    ).toBeTruthy();
    expect(within(autumn).getByText("2 schedules")).toBeTruthy();
    const rows = within(autumn).getAllByRole("row").slice(1);
    expect(
      rows.map((r) => within(r).getAllByRole("cell")[0].textContent),
    ).toEqual(["Autumn A", "Autumn B"]);
    expect(
      within(screen.getByRole("region", { name: "Old" })).getByText("Deleted"),
    ).toBeTruthy();
  });

  it("toggles one group and expands or collapses them all", () => {
    render(<ScheduleGroupsView schedules={SCHEDULES} />);

    fireEvent.click(
      within(screen.getByRole("region", { name: "Spring" })).getAllByRole(
        "button",
      )[0],
    );
    expect(groups().map(([, open]) => open)).toEqual(["true", "true", "false"]);

    fireEvent.click(screen.getByRole("button", { name: "Collapse all" }));
    expect(groups().map(([, open]) => open)).toEqual([
      "false",
      "false",
      "false",
    ]);

    fireEvent.click(screen.getByRole("button", { name: "Expand all" }));
    expect(groups().map(([, open]) => open)).toEqual(["true", "true", "true"]);
  });

  it("pages by dataset group", () => {
    const many = Array.from({ length: 12 }, (_, i) =>
      schedule(`S${i}`, `2026-01-${String(i + 10)}T09:00:00`, `D${i}`),
    );
    render(<ScheduleGroupsView schedules={many} />);
    expect(groups()).toHaveLength(10);
    expect(screen.getByText("Showing 1-10 of 12 datasets")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Next page" }));

    expect(groups().map(([name]) => name)).toEqual(["D1", "D0"]);
  });

  it("searches schedule and dataset names", () => {
    render(<ScheduleGroupsView schedules={SCHEDULES} />);

    fireEvent.change(
      screen.getByPlaceholderText("Search schedules or datasets..."),
      { target: { value: "autumn b" } },
    );

    expect(groups().map(([name]) => name)).toEqual(["Autumn"]);
    expect(screen.getByText("1 schedule")).toBeTruthy();
  });
});
