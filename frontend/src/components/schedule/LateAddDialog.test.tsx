import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type {
  LateAddCandidate,
  LateAddExam,
  LateAddSearchResult,
} from "@/lib/api/schedules";
import { LateAddDialog } from "./LateAddDialog";

vi.mock("@/lib/api/client", () => ({
  apiClient: { schedules: { lateAddSearch: vi.fn() } },
}));

import { apiClient } from "@/lib/api/client";

const lateAddSearch = vi.mocked(apiClient.schedules.lateAddSearch);

const TIMES = ["9AM-11AM", "11:30AM-1:30PM", "2PM-4PM", "4:30PM-6:30PM"];
const DAYS = ["Monday", "Tuesday", "Wednesday"];

const NO_CONFLICTS = {
  student_double_book: 0,
  student_over_daily_limit: 0,
  instructor_double_book: 0,
  instructor_over_daily_limit: 0,
  back_to_back_students: 0,
  back_to_back_instructor: 0,
  large_course_late: 0,
};

function candidate(
  day: number,
  block: number,
  extra: Partial<LateAddCandidate> = {},
): LateAddCandidate {
  return {
    day,
    day_name: DAYS[day],
    block,
    block_time: TIMES[block],
    room: { name: `Room ${day}${block}`, capacity: 40 },
    other_rooms: [],
    clear: true,
    conflicts: NO_CONFLICTS,
    students: { double_book: [], over_daily_limit: [], back_to_back: [] },
    instructor: {
      double_book_crns: [],
      exams_that_day: 1,
      over_daily_limit: false,
      back_to_back: false,
      day_blocks: [],
    },
    large_course_late: false,
    ...extra,
  };
}

function exam(crn: string, day: number | null, block: number | null) {
  return {
    crn,
    course_code: "CS 1000",
    instructor: "I-1",
    size: 20,
    day,
    day_name: day === null ? null : DAYS[day],
    block,
    block_time: block === null ? null : TIMES[block],
    room: day === null ? null : "Hall A",
  } satisfies LateAddExam;
}

function result(extra: Partial<LateAddSearchResult>): LateAddSearchResult {
  return {
    schedule_id: "s1",
    crn: "90001",
    course_code: "CS 1000",
    instructor_id: "I-1",
    size: 30,
    outcome: "clear",
    settings: {
      max_days: 3,
      blocks_per_day: 4,
      student_max_per_day: 2,
      instructor_max_per_day: 2,
    },
    candidates: [],
    no_room_blocks: [],
    instructor_exams: [],
    sibling_sections: [],
    notes: [],
    ...extra,
  };
}

function openDialog() {
  render(<LateAddDialog scheduleId="s1" scheduleName="Fall" />);
  fireEvent.click(screen.getByRole("button", { name: "Late Add" }));
}

function fillForm(crn = "90001", course = "CS 1000", instructor = "I-1") {
  fireEvent.change(screen.getByLabelText("CRN"), { target: { value: crn } });
  fireEvent.change(screen.getByLabelText("Course code"), {
    target: { value: course },
  });
  fireEvent.change(screen.getByLabelText("Instructor ID"), {
    target: { value: instructor },
  });
}

async function search(found: LateAddSearchResult) {
  lateAddSearch.mockResolvedValue(found);
  openDialog();
  fillForm();
  fireEvent.click(screen.getByRole("button", { name: "Find blocks" }));
  await screen.findByRole("heading", { level: 3 });
}

const candidateRow = (day: number, block: number) =>
  screen.getByTestId(`candidate-${day}-${block}`);

describe("LateAddDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("is disabled with the reason when the dataset was deleted", () => {
    render(<LateAddDialog scheduleId="s1" datasetDeleted />);

    const button = screen.getByRole("button", { name: "Late Add" });
    expect(button).toHaveProperty("disabled", true);
    expect(button.parentElement?.title).toMatch(/dataset .* was deleted/);
    fireEvent.click(button);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("enables Find blocks only when every field has a value", () => {
    openDialog();
    const find = screen.getByRole("button", { name: "Find blocks" });
    expect(find).toHaveProperty("disabled", true);

    fillForm("90001", "CS 1000", "   ");
    expect(find).toHaveProperty("disabled", true);

    fillForm();
    expect(find).toHaveProperty("disabled", false);
  });

  it("shows clear blocks in rank order with the instructor and sibling lines", async () => {
    await search(
      result({
        outcome: "clear",
        candidates: [candidate(1, 0), candidate(0, 2)],
        instructor_exams: [exam("100", 0, 1), exam("101", null, null)],
        sibling_sections: [exam("200", 2, 3), exam("201", null, null)],
        notes: ["CRN 90001 has no enrollment rows in courses.csv."],
      }),
    );

    expect(lateAddSearch).toHaveBeenCalledWith("s1", {
      crn: "90001",
      course_code: "CS 1000",
      instructor_id: "I-1",
    });
    expect(screen.getByRole("heading", { level: 3 }).textContent).toContain(
      "Clear blocks found",
    );
    expect(
      screen.getByText("2 exams for this instructor in this schedule"),
    ).toBeTruthy();
    expect(
      screen.getByText(
        "Other sections of CS 1000: CRN 200 (Wednesday 4:30PM-6:30PM), CRN 201 (unscheduled)",
      ),
    ).toBeTruthy();
    expect(
      screen.getByText("CRN 90001 has no enrollment rows in courses.csv."),
    ).toBeTruthy();

    const radios = screen.getAllByRole("radio");
    expect(radios.map((radio) => radio.parentElement?.textContent)).toEqual([
      "1.Tuesday 9AM-11AM",
      "2.Monday 2PM-4PM",
    ]);
    // The best block starts selected.
    expect(radios[0]).toHaveProperty("checked", true);
    expect(within(candidateRow(1, 0)).getByText("No conflicts")).toBeTruthy();
    expect(
      within(candidateRow(1, 0)).getByText("Room 10 (capacity 40)"),
    ).toBeTruthy();
  });

  it("says when the instructor has no exams in the schedule", async () => {
    await search(result({ candidates: [candidate(0, 0)] }));

    expect(
      screen.getByText("No exams for this instructor in this schedule"),
    ).toBeTruthy();
    expect(screen.queryByText(/Other sections/)).toBeNull();
  });

  it("styles least-conflicts hard counts as warnings and lists only non-zero types", async () => {
    await search(
      result({
        outcome: "least_conflicts",
        candidates: [
          candidate(0, 1, {
            clear: false,
            conflicts: {
              ...NO_CONFLICTS,
              student_double_book: 2,
              back_to_back_students: 1,
              large_course_late: 1,
            },
            students: {
              double_book: [
                { student_id: "00012", crns: ["300"] },
                { student_id: "00034", crns: ["300", "301"] },
              ],
              over_daily_limit: [],
              back_to_back: [{ student_id: "00056", blocks: [0, 1] }],
            },
            large_course_late: true,
          }),
        ],
      }),
    );

    expect(screen.getByRole("heading", { level: 3 }).textContent).toContain(
      "No clear block, fewest conflicts first",
    );
    const row = candidateRow(0, 1);
    const double = within(row).getByRole("button", {
      name: "Student double-book: 2 students",
    });
    expect(double.closest("li")?.className).toContain("text-amber-600");
    const backToBack = within(row).getByRole("button", {
      name: "Student back-to-back: 1 student",
    });
    expect(backToBack.closest("li")?.className).not.toContain("text-amber-600");
    // No people behind it: plain text, not a toggle.
    expect(within(row).getByText("Large course in a late block").tagName).toBe(
      "LI",
    );
    expect(within(row).queryByText(/per-day limit/)).toBeNull();
    expect(within(row).queryByText(/Instructor/)).toBeNull();
  });

  it("expands and collapses the people behind a count, with copy buttons", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });
    await search(
      result({
        outcome: "least_conflicts",
        candidates: [
          candidate(0, 1, {
            clear: false,
            conflicts: {
              ...NO_CONFLICTS,
              student_double_book: 2,
              instructor_over_daily_limit: 1,
              back_to_back_instructor: 1,
            },
            students: {
              double_book: [
                { student_id: "00012", crns: ["300"] },
                { student_id: "00034", crns: ["300", "301"] },
              ],
              over_daily_limit: [],
              back_to_back: [],
            },
            instructor: {
              double_book_crns: [],
              exams_that_day: 3,
              over_daily_limit: true,
              back_to_back: true,
              // Block 2 is named nowhere in the response.
              day_blocks: [1, 2],
            },
          }),
        ],
      }),
    );
    const row = candidateRow(0, 1);
    const toggle = within(row).getByRole("button", {
      name: "Student double-book: 2 students",
    });
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    expect(within(row).queryByText("00012")).toBeNull();

    fireEvent.click(toggle);
    expect(toggle.getAttribute("aria-expanded")).toBe("true");
    expect(within(row).getByText("00012")).toBeTruthy();
    expect(within(row).getByText("also in CRN 300, 301")).toBeTruthy();

    await act(async () => {
      fireEvent.click(within(row).getByRole("button", { name: "Copy 00034" }));
    });
    expect(writeText).toHaveBeenLastCalledWith("00034");
    await act(async () => {
      fireEvent.click(
        within(row).getByRole("button", {
          name: "Copy all IDs: Student double-book",
        }),
      );
    });
    expect(writeText).toHaveBeenLastCalledWith("00012\n00034");

    fireEvent.click(toggle);
    expect(within(row).queryByText("00012")).toBeNull();

    fireEvent.click(
      within(row).getByRole("button", { name: "Instructor per-day limit" }),
    );
    expect(within(row).getByText("3 exams that day")).toBeTruthy();
    fireEvent.click(
      within(row).getByRole("button", { name: "Instructor back-to-back" }),
    );
    expect(within(row).getByText("11:30AM-1:30PM, block 3")).toBeTruthy();
    // One person: no "Copy all".
    expect(within(row).queryByText("Copy all")).toBeNull();
    expect(
      within(row).getAllByRole("button", { name: "Copy I-1" }),
    ).toHaveLength(2);
  });

  it("picks another fitting room, which also selects that block", async () => {
    // Radix Select calls these DOM APIs, which jsdom lacks.
    Element.prototype.hasPointerCapture ??= () => false;
    Element.prototype.scrollIntoView ??= () => {};
    await search(
      result({
        candidates: [
          candidate(0, 0),
          candidate(1, 1, {
            other_rooms: [
              { name: "Big Hall", capacity: 80 },
              { name: "Huge Hall", capacity: 200 },
            ],
          }),
        ],
      }),
    );
    expect(candidateRow(0, 0).dataset.selected).toBe("true");
    expect(within(candidateRow(0, 0)).queryByRole("combobox")).toBeNull();

    const picker = screen.getByRole("combobox", {
      name: "Room for Tuesday 11:30AM-1:30PM",
    });
    expect(picker.textContent).toContain("Room 11 (capacity 40) · best fit");
    fireEvent.keyDown(picker, { key: "Enter" });
    expect(
      screen.getAllByRole("option").map((option) => option.textContent),
    ).toEqual([
      "Room 11 (capacity 40) · best fit",
      "Big Hall (capacity 80)",
      "Huge Hall (capacity 200)",
    ]);
    fireEvent.keyDown(
      screen.getByRole("option", { name: "Huge Hall (capacity 200)" }),
      { key: "Enter" },
    );

    expect(picker.textContent).toContain("Huge Hall (capacity 200)");
    expect(candidateRow(1, 1).dataset.selected).toBe("true");
    expect(candidateRow(0, 0).dataset.selected).toBe("false");

    // Picking another block keeps the room chosen for this one.
    fireEvent.click(screen.getAllByRole("radio")[0]);
    expect(candidateRow(0, 0).dataset.selected).toBe("true");
    expect(picker.textContent).toContain("Huge Hall (capacity 200)");
  });

  it("shows the largest free room per block when no room fits", async () => {
    await search(
      result({
        outcome: "no_room",
        no_room_blocks: [
          {
            day: 0,
            day_name: "Monday",
            block: 0,
            block_time: TIMES[0],
            largest_free_room: { name: "Small Room", capacity: 12 },
          },
          {
            day: 0,
            day_name: "Monday",
            block: 1,
            block_time: TIMES[1],
            largest_free_room: null,
          },
        ],
      }),
    );

    expect(screen.getByRole("heading", { level: 3 }).textContent).toContain(
      "No block has a free room that fits",
    );
    expect(screen.getByText("Monday 9AM-11AM:").textContent).toBe(
      "Monday 9AM-11AM: Small Room (capacity 12)",
    );
    expect(screen.getByText("Monday 11:30AM-1:30PM:").textContent).toBe(
      "Monday 11:30AM-1:30PM: no free room",
    );
    expect(screen.queryAllByRole("radio")).toHaveLength(0);
  });

  it("shows a server error inline and clears it on the next search", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    lateAddSearch.mockRejectedValueOnce(
      new Error("CRN 90001 is already in this schedule (Monday 9AM-11AM)."),
    );
    openDialog();
    fillForm();
    fireEvent.click(screen.getByRole("button", { name: "Find blocks" }));

    expect((await screen.findByRole("alert")).textContent).toContain(
      "CRN 90001 is already in this schedule (Monday 9AM-11AM).",
    );
    expect(screen.queryByRole("heading", { level: 3 })).toBeNull();

    lateAddSearch.mockResolvedValueOnce(
      result({ candidates: [candidate(0, 0)] }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Find blocks" }));
    await screen.findByRole("heading", { level: 3 });
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("drops a reply that arrives after the dialog was closed", async () => {
    const pending = Promise.withResolvers<LateAddSearchResult>();
    lateAddSearch.mockReturnValueOnce(pending.promise);
    openDialog();
    fillForm();
    fireEvent.click(screen.getByRole("button", { name: "Find blocks" }));
    expect(screen.getByRole("button", { name: /Searching/ })).toHaveProperty(
      "disabled",
      true,
    );

    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
    fireEvent.click(screen.getByRole("button", { name: "Late Add" }));
    await act(async () =>
      pending.resolve(result({ candidates: [candidate(0, 0)] })),
    );

    expect(screen.queryByRole("heading", { level: 3 })).toBeNull();
    expect(screen.getByLabelText("CRN")).toHaveProperty("value", "");
    expect(screen.getByRole("button", { name: "Find blocks" })).toHaveProperty(
      "disabled",
      true,
    );
  });
});
