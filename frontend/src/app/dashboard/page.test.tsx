import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import type { ScheduleListItem } from "@/lib/api/schedules";
import { useSchedulesStore } from "@/lib/store/schedulesStore";
import { useSchedulesViewStore } from "@/lib/store/schedulesViewStore";
import DashboardPage from "./page";

const schedule = (
  name: string,
  createdAt: string,
  extra: Partial<ScheduleListItem> = {},
  dataset = "Spring",
): ScheduleListItem => ({
  schedule_id: name.toLowerCase().replace(/ /g, "-"),
  schedule_name: name,
  created_at: createdAt,
  algorithm: "DSATUR",
  parameters: {},
  status: "Completed",
  dataset_id: dataset,
  dataset: {
    name: dataset,
    uploaded_at: "2026-01-01T00:00:00",
    deleted: dataset === "Retired",
    courses: 10,
    students: 100,
    rooms: 5,
  },
  total_exams: 10,
  late_add_count: 0,
  based_on_name: null,
  ...extra,
});

// Newest first, the list shows Running, Failed and Plan 12-05 on page 1, then
// Plan 04-01, the shared plan and the deleted dataset's plan on page 2.
const SCHEDULES = [
  ...Array.from({ length: 12 }, (_, i) =>
    schedule(
      `Plan ${String(i + 1).padStart(2, "0")}`,
      `2026-02-${String(i + 1).padStart(2, "0")}T09:00:00`,
    ),
  ),
  schedule("Running plan", "2026-03-01T09:00:00", { status: "Running" }),
  schedule("Failed plan", "2026-02-28T09:00:00", { status: "Failed" }),
  schedule(
    "Shared plan",
    "2026-01-20T09:00:00",
    { is_shared: true, is_owner: false, shared_by_user_name: "Sam" },
    "Summer",
  ),
  schedule("Retired plan", "2026-01-10T09:00:00", {}, "Retired"),
];

const box = (name: string) =>
  screen.getByRole("checkbox", { name: `Select ${name}` });
const toggle = (name: string) => fireEvent.click(box(name));
const isChecked = (name: string) =>
  box(name).getAttribute("aria-checked") === "true";
const isDisabled = (name: string) => box(name).hasAttribute("disabled");
const reason = (name: string) =>
  box(name).closest("[title]")?.getAttribute("title");
const compareHref = () =>
  screen.getByRole("link", { name: "Compare" }).getAttribute("href");

const renderPage = async () => {
  render(<DashboardPage />);
  // Let the (stubbed) schedule fetch settle.
  await act(async () => {});
};

beforeEach(() => {
  useSchedulesViewStore.setState({
    view: "list",
    pageSize: 10,
    datasetPageSize: 10,
    selectedIds: [],
  });
  sessionStorage.clear();
  useSchedulesStore.setState({
    schedules: SCHEDULES,
    isLoadingList: false,
    error: null,
    fetchSchedules: async () => {},
  });
});

describe("Dashboard schedule selection for Compare", () => {
  it("keeps picks across pages, search and sorting", async () => {
    await renderPage();

    toggle("Plan 12");
    expect(screen.getByText("1 selected")).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "Compare" }).hasAttribute("disabled"),
    ).toBe(true);

    fireEvent.click(screen.getAllByRole("button", { name: "Next page" })[0]);
    // Shared schedules can be compared too.
    toggle("Shared plan");

    fireEvent.change(screen.getByPlaceholderText("Search schedules..."), {
      target: { value: "plan 03" },
    });
    toggle("Plan 03");
    fireEvent.change(screen.getByPlaceholderText("Search schedules..."), {
      target: { value: "" },
    });
    expect(isChecked("Plan 12")).toBe(true);

    fireEvent.click(screen.getByRole("button", { name: /Schedule Name/ }));
    expect(isChecked("Plan 03")).toBe(true);
    expect(screen.getByText("3 selected")).toBeTruthy();
    expect(compareHref()).toBe(
      "/dashboard/compare?ids=plan-12,shared-plan,plan-03",
    );
  });

  it("shares picks between the views, in the order they were picked", async () => {
    await renderPage();
    toggle("Plan 12");

    fireEvent.click(screen.getByRole("button", { name: "By dataset" }));
    fireEvent.click(screen.getByRole("button", { name: "Expand all" }));
    expect(isChecked("Plan 12")).toBe(true);
    toggle("Shared plan");
    // A schedule whose dataset was deleted can still be compared.
    toggle("Retired plan");

    // Unpicking and picking again moves a schedule to the end.
    toggle("Plan 12");
    toggle("Plan 12");
    expect(compareHref()).toBe(
      "/dashboard/compare?ids=shared-plan,retired-plan,plan-12",
    );

    fireEvent.click(screen.getByRole("button", { name: "List" }));
    expect(isChecked("Plan 12")).toBe(true);
    expect(screen.getByText("3 selected")).toBeTruthy();
  });

  it("stops at 4 picks and says why the rest are disabled", async () => {
    await renderPage();
    for (const name of ["Plan 12", "Plan 11", "Plan 10", "Plan 09"]) {
      toggle(name);
    }

    expect(isDisabled("Plan 08")).toBe(true);
    expect(reason("Plan 08")).toBe("You can compare up to 4 schedules");
    toggle("Plan 08");
    expect(screen.getByText("4 selected")).toBeTruthy();
    // Picked ones can still be unpicked.
    expect(isDisabled("Plan 09")).toBe(false);

    toggle("Plan 09");
    expect(isDisabled("Plan 08")).toBe(false);
    expect(reason("Plan 08")).toBeUndefined();
  });

  it("does not let running or failed schedules be picked", async () => {
    await renderPage();

    for (const name of ["Running plan", "Failed plan"]) {
      expect(isDisabled(name)).toBe(true);
      expect(reason(name)).toBe("Only completed schedules can be compared");
    }
    toggle("Running plan");
    expect(screen.queryByText(/selected$/)).toBeNull();
  });

  it("restores this session's picks without schedules no longer listed, and clears them", async () => {
    sessionStorage.setItem(
      "schedules-view-storage",
      JSON.stringify({
        state: {
          selectedIds: ["plan-02", "deleted-since", "running-plan", "plan-01"],
        },
        version: 0,
      }),
    );
    await renderPage();

    expect(screen.getByText("2 selected")).toBeTruthy();
    expect(compareHref()).toBe("/dashboard/compare?ids=plan-02,plan-01");

    fireEvent.click(screen.getByRole("button", { name: "Clear" }));
    expect(screen.queryByText(/selected$/)).toBeNull();
    fireEvent.click(screen.getAllByRole("button", { name: "Next page" })[0]);
    expect(isChecked("Plan 02")).toBe(false);
  });
});
