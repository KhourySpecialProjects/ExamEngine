import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { useState } from "react";
import { beforeEach, describe, expect, it, type Mock, vi } from "vitest";
import type {
  ConflictBreakdown,
  ScheduleExam,
  ScheduleSummary,
} from "@/lib/api/schedules";
import { useConflictViewStore } from "@/lib/store/conflictViewStore";
import { useSchedulesStore } from "@/lib/store/schedulesStore";
import ConflictView from "./ConflictView";

vi.mock("@/lib/store/schedulesStore", () => ({
  useSchedulesStore: vi.fn(),
}));

const doubleBook = (
  student: string,
  day: string,
  crn: string,
  conflictingCrn: string,
): ConflictBreakdown => ({
  conflict_type: "student_double_book",
  entity_id: student,
  day,
  block: 0,
  block_time: "9AM-11AM",
  crn,
  course: `CS ${crn}`,
  conflicting_crn: conflictingCrn,
  conflicting_course: `CS ${conflictingCrn}`,
});

const noConflicts = Object.fromEntries(
  [
    "student_double_book",
    "instructor_double_book",
    "student_over_daily_limit",
    "instructor_over_daily_limit",
    "student_back_to_back",
    "instructor_back_to_back",
    "large_courses_late",
  ].map((metric) => [metric, { people: 0, instances: 0 }]),
) as ScheduleSummary["conflicts"];

function mockSchedule(
  breakdown: ConflictBreakdown[],
  complete: ScheduleExam[] = [],
  conflicts: Partial<ScheduleSummary["conflicts"]> = {},
) {
  const currentSchedule = {
    conflicts: { total: breakdown.length, details: {}, breakdown },
    schedule: { complete, calendar: {}, total_exams: complete.length },
    summary: { conflicts: { ...noConflicts, ...conflicts } },
  };
  // Only currentSchedule is read by the conflict view.
  const state = { currentSchedule } as unknown as Parameters<
    Parameters<typeof useSchedulesStore>[0]
  >[0];
  vi.mocked(useSchedulesStore).mockImplementation((selector) =>
    selector(state),
  );
}

const bodyRows = () => {
  const [, ...rows] = within(screen.getByRole("table")).getAllByRole("row");
  return rows;
};

const cellTexts = (row: HTMLElement) =>
  within(row)
    .getAllByRole("cell")
    .map((td) => td.textContent);

const pillTitles = (row: HTMLElement) =>
  [...row.querySelectorAll('[data-slot="badge"]')].map((b) =>
    b.getAttribute("title"),
  );

// The schedule page keeps the selected type in the URL; tests keep it here.
function ConflictViewWithLocalType() {
  const [type, setType] = useState<string | null>(null);
  return <ConflictView type={type} onTypeChange={setType} />;
}

const renderView = () => render(<ConflictViewWithLocalType />);

describe("ConflictView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
    useConflictViewStore.setState({ pageSize: 10 });
    mockSchedule(
      [
        doubleBook("000000001", "Tuesday", "3500", "4535"),
        doubleBook("000000001", "Monday", "2500", "2510"),
        doubleBook("000000001", "Monday", "2800", "2510"),
        doubleBook("000000002", "Monday", "3500", "4535"),
      ],
      [
        {
          CRN: "2500",
          Course: "CS 2500",
          Day: "Monday",
          Block: "0",
          Room: "WVH 210",
          Capacity: 120,
          Size: 95,
          Valid: true,
          Instructor: "Dr. Smith",
        },
      ],
    );
  });

  it("groups each student's conflicts as sub-rows spanned by NUId and count", () => {
    renderView();

    expect(
      within(screen.getByRole("table"))
        .getAllByRole("columnheader")
        .map((th) => th.textContent),
    ).toEqual(["NUId", "Conflicts", "Day", "Time", "Conflicting exams"]);

    const rows = bodyRows();
    expect(rows).toHaveLength(3);

    // Student 1: NUId + count on the first sub-row only, spanning both.
    const [first] = within(rows[0]).getAllByRole("cell");
    expect(first.getAttribute("rowspan")).toBe("2");
    expect(cellTexts(rows[0]).slice(0, 4)).toEqual([
      "000000001",
      "2",
      "Monday",
      "9AM-11AM",
    ]);
    expect(pillTitles(rows[0])).toEqual([
      "CS 2500 · CRN 2500\nRoom: WVH 210 (capacity 120)\nEnrolled: 95\nInstructor: Dr. Smith",
      "CS 2510 · CRN 2510",
      "CS 2800 · CRN 2800",
    ]);
    expect(cellTexts(rows[1]).slice(0, 2)).toEqual(["Tuesday", "9AM-11AM"]);
    expect(pillTitles(rows[1])).toEqual([
      "CS 3500 · CRN 3500",
      "CS 4535 · CRN 4535",
    ]);

    expect(cellTexts(rows[2]).slice(0, 4)).toEqual([
      "000000002",
      "1",
      "Monday",
      "9AM-11AM",
    ]);

    // Pagination bars above and below the table.
    expect(screen.getAllByText("Showing 1-2 of 2 students")).toHaveLength(2);
  });

  describe("pagination", () => {
    // 30 students, one double-book each, zero-padded like real NUIds.
    const thirtyStudents = () =>
      mockSchedule(
        Array.from({ length: 30 }, (_, i) =>
          doubleBook(String(i + 1).padStart(9, "0"), "Monday", "1", "2"),
        ),
      );
    const firstEntity = () => cellTexts(bodyRows()[0])[0];

    it("pages 10 students at a time with first/prev/next/last controls", () => {
      thirtyStudents();
      renderView();

      const [first, prev, next, last] = [
        "First page",
        "Previous page",
        "Next page",
        "Last page",
      ].map((name) => screen.getAllByRole("button", { name })[0]);
      expect(bodyRows()).toHaveLength(10);
      expect(screen.getAllByText("Page 1 of 3")).toHaveLength(2);
      expect([first, prev].every((b) => b.hasAttribute("disabled"))).toBe(true);

      fireEvent.click(next);
      expect(firstEntity()).toBe("000000011");
      expect(screen.getAllByText("Showing 11-20 of 30 students")).toHaveLength(
        2,
      );

      fireEvent.click(last);
      expect(firstEntity()).toBe("000000021");
      expect(next.hasAttribute("disabled")).toBe(true);

      // The bottom bar drives the same state.
      fireEvent.click(screen.getAllByRole("button", { name: "First page" })[1]);
      expect(firstEntity()).toBe("000000001");
    });

    const chooseRowsPerPage = (size: string) => {
      // Radix Select calls these DOM APIs, which jsdom lacks.
      Element.prototype.hasPointerCapture ??= () => false;
      Element.prototype.scrollIntoView ??= () => {};
      fireEvent.keyDown(
        screen.getByRole("combobox", { name: "Rows per page" }),
        { key: "Enter" },
      );
      fireEvent.keyDown(screen.getByRole("option", { name: size }), {
        key: "Enter",
      });
    };

    it("changing rows per page shows that many rows from page 1 and saves it for the session", () => {
      thirtyStudents();
      renderView();
      fireEvent.click(screen.getAllByRole("button", { name: "Next page" })[0]);

      chooseRowsPerPage("25");

      expect(bodyRows()).toHaveLength(25);
      expect(firstEntity()).toBe("000000001");
      expect(screen.getAllByText("Page 1 of 2")).toHaveLength(2);
      expect(
        JSON.parse(sessionStorage.getItem("conflict-view-storage") ?? "{}")
          .state?.pageSize,
      ).toBe(25);
    });

    it("still changes rows per page when the session can't be saved", () => {
      thirtyStudents();
      renderView();
      fireEvent.click(screen.getAllByRole("button", { name: "Next page" })[0]);
      const setItem = vi
        .spyOn(Storage.prototype, "setItem")
        .mockImplementation(() => {
          throw new DOMException("full", "QuotaExceededError");
        });

      chooseRowsPerPage("25");
      setItem.mockRestore();

      expect(bodyRows()).toHaveLength(25);
      expect(firstEntity()).toBe("000000001");
    });

    it("restores rows per page saved earlier in this browser session", async () => {
      sessionStorage.setItem(
        "conflict-view-storage",
        JSON.stringify({ state: { pageSize: 50 }, version: 0 }),
      );
      await useConflictViewStore.persist.rehydrate();
      thirtyStudents();
      renderView();

      expect(bodyRows()).toHaveLength(30);
      expect(screen.getAllByText("Page 1 of 1")).toHaveLength(2);
    });

    it("ignores a saved rows-per-page that is not an offered size", async () => {
      sessionStorage.setItem(
        "conflict-view-storage",
        JSON.stringify({ state: { pageSize: 0 }, version: 0 }),
      );
      await useConflictViewStore.persist.rehydrate();
      thirtyStudents();
      renderView();

      expect(bodyRows()).toHaveLength(10);
      expect(screen.getAllByText("Page 1 of 3")).toHaveLength(2);
    });
  });

  it("shows back-to-back time slots as pills when records have no courses", () => {
    mockSchedule([
      {
        conflict_type: "back_to_back_student",
        student_id: "000000004",
        day: "Wednesday",
        blocks: [0, 1],
        block_times: ["9AM-11AM", "11:30AM-1:30PM"],
      },
    ]);
    renderView();

    expect(
      within(screen.getByRole("table"))
        .getAllByRole("columnheader")
        .map((th) => th.textContent),
    ).toEqual(["NUId", "Conflicts", "Day", "Exam times"]);
    const [row] = bodyRows();
    expect(
      [...row.querySelectorAll('[data-slot="badge"]')].map(
        (b) => b.textContent,
      ),
    ).toEqual(["9AM-11AM", "11:30AM-1:30PM"]);
  });

  it("shows a repeated back-to-back time slot twice without a React key warning", () => {
    // Real record: the student also has two exams in block 1 (double-booked).
    const consoleError = vi
      .spyOn(console, "error")
      .mockImplementation(() => {});
    mockSchedule([
      {
        conflict_type: "back_to_back",
        student_id: "000102290",
        day: "Monday",
        blocks: [1, 1, 2],
        block_times: ["11:30AM-1:30PM", "11:30AM-1:30PM", "2PM-4PM"],
      },
    ]);
    renderView();

    const [row] = bodyRows();
    expect(
      [...row.querySelectorAll('[data-slot="badge"]')].map(
        (b) => b.textContent,
      ),
    ).toEqual(["11:30AM-1:30PM", "11:30AM-1:30PM", "2PM-4PM"]);
    expect(
      consoleError.mock.calls.filter((args) =>
        String(args[0]).includes("same key"),
      ),
    ).toEqual([]);
    consoleError.mockRestore();
  });

  it("lists per-day limit conflicts as the days a person is over the limit", () => {
    // Backend shape: one record per exam that went over the limit (EXENG-46).
    const overLimit = (day: string, block: number, crn: string) => ({
      conflict_type: "student_gt_max_per_day",
      entity_id: "000100663",
      student_id: "000100663",
      day,
      block,
      block_time: ["9AM-11AM", "11:30AM-1:30PM", "2PM-4PM"][block],
      crn,
      course: `CS ${crn}`,
    });
    mockSchedule([
      overLimit("Tuesday", 2, "3"),
      overLimit("Monday", 1, "1"),
      overLimit("Monday", 2, "2"),
    ]);
    renderView();

    expect(
      within(screen.getByRole("table"))
        .getAllByRole("columnheader")
        .map((th) => th.textContent),
    ).toEqual(["NUId", "Days over limit", "Day"]);
    // Two over-limit exams on Monday are one day over the limit.
    expect(bodyRows().map(cellTexts)).toEqual([
      ["000100663", "2", "Monday"],
      ["Tuesday"],
    ]);
    expect(screen.queryAllByText("CS 1")).toEqual([]);
  });

  it("orders tabs students, then instructors, then courses, each named for who it affects", () => {
    // conflict_type values from backend/src/domain/assemblers/conflict_assembler.py,
    // deliberately out of order.
    mockSchedule(
      [
        "large_course_not_early",
        "back_to_back_instructor",
        "instructor_double_book",
        "back_to_back",
        "instructor_gt_max_per_day",
        "student_gt_max_per_day",
        "student_double_book",
      ].map((conflict_type) => ({
        conflict_type,
        entity_id: "x",
        day: "Monday",
      })),
    );
    renderView();

    const tabs = screen
      .getAllByRole("button")
      .map((b) => b.textContent)
      .filter((t) => /^(Student|Instructor|Large)/.test(t ?? ""));
    expect(tabs).toEqual([
      "Student Double-Book",
      "Student Per-Day Limit",
      "Student Back-to-Back",
      "Instructor Double-Book",
      "Instructor Per-Day Limit",
      "Instructor Back-to-Back",
      "Large Course Not Early",
    ]);
  });

  it("opens the type it is given, the first tab for an unknown one, and reports tab picks", () => {
    mockSchedule([
      doubleBook("000000001", "Monday", "2500", "2510"),
      {
        ...doubleBook("Dr. Smith", "Tuesday", "3500", "4535"),
        conflict_type: "instructor_double_book",
      },
    ]);
    const onTypeChange = vi.fn();
    const { rerender } = render(
      <ConflictView
        type="instructor_double_book"
        onTypeChange={onTypeChange}
      />,
    );
    const selected = () =>
      within(screen.getByRole("group", { name: "Conflict types" }))
        .getAllByRole("button", { pressed: true })
        .map((b) => b.textContent);

    expect(selected()).toEqual(["Instructor Double-Book"]);
    expect(cellTexts(bodyRows()[0])[0]).toContain("Dr. Smith");

    rerender(<ConflictView type="no_such_type" onTypeChange={onTypeChange} />);
    expect(selected()).toEqual(["Student Double-Book"]);
    expect(cellTexts(bodyRows()[0])[0]).toContain("000000001");

    fireEvent.click(
      screen.getByRole("button", { name: "Instructor Double-Book" }),
    );
    expect(onTypeChange).toHaveBeenCalledWith("instructor_double_book");
  });

  describe("sorting", () => {
    const sortBy = (label: string) =>
      fireEvent.click(screen.getByRole("button", { name: label }));
    const header = (label: string) =>
      screen
        .getAllByRole("columnheader")
        .find((th) => th.textContent === label);

    it("sorts people both ways by a header, keeping each person's sub-rows together", () => {
      renderView();

      sortBy("Conflicts");
      expect(header("Conflicts")?.getAttribute("aria-sort")).toBe("ascending");
      expect(bodyRows().map((r) => cellTexts(r)[0])).toEqual([
        "000000002",
        "000000001",
        "Tuesday",
      ]);

      sortBy("Conflicts");
      expect(header("Conflicts")?.getAttribute("aria-sort")).toBe("descending");
      const rows = bodyRows();
      expect(
        within(rows[0]).getAllByRole("cell")[0].getAttribute("rowspan"),
      ).toBe("2");
      expect(rows.map((r) => cellTexts(r)[0])).toEqual([
        "000000001",
        "Tuesday",
        "000000002",
      ]);
    });

    it("does not offer sorting on the exams column", () => {
      renderView();

      expect(
        screen.queryByRole("button", { name: "Conflicting exams" }),
      ).toBeNull();
    });

    it("goes back to page 1 when the sort changes", () => {
      mockSchedule(
        Array.from({ length: 30 }, (_, i) =>
          doubleBook(String(i + 1).padStart(9, "0"), "Monday", "1", "2"),
        ),
      );
      renderView();
      fireEvent.click(screen.getAllByRole("button", { name: "Next page" })[0]);

      sortBy("NUId");
      sortBy("NUId");

      expect(cellTexts(bodyRows()[0])[0]).toBe("000000030");
      expect(screen.getAllByText("Page 1 of 3")).toHaveLength(2);
    });
  });

  describe("by course", () => {
    it("lists each conflicting course once with its distinct students, most first", () => {
      renderView();
      fireEvent.click(screen.getByRole("button", { name: "By course" }));

      expect(
        screen
          .getAllByRole("columnheader")
          .map((th) => [th.textContent, th.getAttribute("aria-sort")]),
      ).toEqual([
        ["Course", null],
        ["CRN", null],
        ["Students with a conflict", "descending"],
        ["Conflicts", null],
      ]);
      // CRN 3500 and 4535 are shared by both students; 2510 is in two of
      // student 1's records but on the same Monday slot: one conflict.
      expect(bodyRows().map(cellTexts)).toEqual([
        ["CS 3500", "3500", "2", "2"],
        ["CS 4535", "4535", "2", "2"],
        ["CS 2500", "2500", "1", "1"],
        ["CS 2510", "2510", "1", "1"],
        ["CS 2800", "2800", "1", "1"],
      ]);
      expect(screen.getAllByText("Showing 1-5 of 5 courses")).toHaveLength(2);
    });

    it("says back-to-back conflicts can't be counted per course instead of showing none", () => {
      mockSchedule([
        {
          conflict_type: "back_to_back_student",
          student_id: "000000004",
          day: "Wednesday",
          blocks: [0, 1],
          block_times: ["9AM-11AM", "11:30AM-1:30PM"],
        },
      ]);
      renderView();
      fireEvent.click(screen.getByRole("button", { name: "By course" }));

      expect(screen.queryByRole("table")).toBeNull();
      expect(
        screen.getByText(/can't be counted per course/).textContent,
      ).toMatch(/^Back-to-back conflicts/);
    });
  });

  describe("copy and course details", () => {
    let writeText: Mock<(text: string) => Promise<void>>;
    beforeEach(() => {
      writeText = vi
        .fn<(text: string) => Promise<void>>()
        .mockResolvedValue(undefined);
      Object.defineProperty(navigator, "clipboard", {
        value: { writeText },
        configurable: true,
      });
    });

    it("copies the exact NUId and CRN without opening the course details", async () => {
      renderView();

      fireEvent.click(
        screen.getByRole("button", { name: "Copy NUId 000000002" }),
      );
      fireEvent.click(
        screen.getAllByRole("button", { name: "Copy CRN 2510" })[0],
      );

      await waitFor(() =>
        expect(writeText.mock.calls).toEqual([["000000002"], ["2510"]]),
      );
      expect(screen.queryByRole("dialog")).toBeNull();
    });

    it("opens a course's details from its pill with the students it conflicts for", async () => {
      renderView();

      // CS 3500 is double-booked for both students.
      fireEvent.click(
        screen.getAllByRole("button", {
          name: "Show conflicts for CS 3500",
        })[0],
      );
      const dialog = screen.getByRole("dialog");
      expect(
        within(dialog).getByRole("heading", { name: "CS 3500" }),
      ).toBeTruthy();
      const section = within(dialog).getByRole("region", {
        name: "Student Double-Book",
      });
      expect(within(section).getByRole("heading").textContent).toBe(
        "Student Double-Book: 2 students",
      );
      expect(
        within(section)
          .getAllByRole("listitem")
          .map((li) => li.textContent),
      ).toEqual(["000000001", "000000002"]);

      fireEvent.click(
        within(section).getByRole("button", { name: "Copy all" }),
      );
      await waitFor(() =>
        expect(writeText).toHaveBeenCalledWith("000000001\n000000002"),
      );
    });

    it("counts each course of a 3-way double-book, with exam details in the header", () => {
      renderView();

      // Student 1's Monday slot holds CS 2500, CS 2510 and CS 2800.
      fireEvent.click(
        screen.getByRole("button", {
          name: "Open conflict details for CS 2500",
        }),
      );
      const dialog = screen.getByRole("dialog");
      expect(dialog.textContent).toContain("CRN 2500");
      expect(dialog.textContent).toContain("Monday Block 0");
      expect(dialog.textContent).toContain("WVH 210");
      expect(dialog.textContent).toContain("95 enrolled");
      expect(
        within(dialog).getByRole("region", { name: "Student Double-Book" })
          .textContent,
      ).toContain("Student Double-Book: 1 student");
    });
  });

  it("shows the server's people count on each card, 0 when it has none", () => {
    mockSchedule([doubleBook("000000001", "Monday", "2500", "2510")], [], {
      student_double_book: { people: 2, instances: 3 },
    });
    renderView();

    const subtitle = screen.getByText("Students with overlapping exams");
    expect(subtitle.previousSibling?.textContent).toBe("2");
    expect(
      screen.getByText("Instructors with overlapping exams").previousSibling
        ?.textContent,
    ).toBe("0");
    // Who is affected is a pill under the title, not part of the title.
    const card = subtitle.closest<HTMLElement>('[data-slot="card"]');
    expect(
      within(card as HTMLElement).getByText("Double-Book").dataset.slot,
    ).toBe("card-title");
    expect(within(card as HTMLElement).getByText("Student").dataset.slot).toBe(
      "badge",
    );
  });
});
