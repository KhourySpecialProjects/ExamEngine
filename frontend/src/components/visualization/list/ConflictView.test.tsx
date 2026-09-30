import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ConflictBreakdown, ScheduleExam } from "@/lib/api/schedules";
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

function mockSchedule(
  breakdown: ConflictBreakdown[],
  complete: ScheduleExam[] = [],
) {
  const currentSchedule = {
    conflicts: { total: breakdown.length, details: {}, breakdown },
    schedule: { complete, calendar: {}, total_exams: complete.length },
  };
  // Only currentSchedule is read by the conflict hook.
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
    render(<ConflictView />);

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
      render(<ConflictView />);

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

    it("changing rows per page shows that many rows from page 1 and saves it for the session", () => {
      // Radix Select calls these DOM APIs, which jsdom lacks.
      Element.prototype.hasPointerCapture ??= () => false;
      Element.prototype.scrollIntoView ??= () => {};
      thirtyStudents();
      render(<ConflictView />);
      fireEvent.click(screen.getAllByRole("button", { name: "Next page" })[0]);

      fireEvent.keyDown(
        screen.getByRole("combobox", { name: "Rows per page" }),
        { key: "Enter" },
      );
      fireEvent.keyDown(screen.getByRole("option", { name: "25" }), {
        key: "Enter",
      });

      expect(bodyRows()).toHaveLength(25);
      expect(firstEntity()).toBe("000000001");
      expect(screen.getAllByText("Page 1 of 2")).toHaveLength(2);
      expect(
        JSON.parse(sessionStorage.getItem("conflict-view-storage") ?? "{}")
          .state?.pageSize,
      ).toBe(25);
    });

    it("restores rows per page saved earlier in this browser session", async () => {
      sessionStorage.setItem(
        "conflict-view-storage",
        JSON.stringify({ state: { pageSize: 50 }, version: 0 }),
      );
      await useConflictViewStore.persist.rehydrate();
      thirtyStudents();
      render(<ConflictView />);

      expect(bodyRows()).toHaveLength(30);
      expect(screen.getAllByText("Page 1 of 1")).toHaveLength(2);
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
    render(<ConflictView />);

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
    render(<ConflictView />);

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
    render(<ConflictView />);

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

  it("counts students, not conflict records, in the student double-book card", () => {
    render(<ConflictView />);

    const subtitle = screen.getByText("Students with overlapping exams");
    expect(subtitle.previousSibling?.textContent).toBe("2");
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
