import { render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
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
) => ({
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

describe("ConflictView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    const currentSchedule = {
      conflicts: {
        total: 4,
        details: {},
        breakdown: [
          doubleBook("000000001", "Tuesday", "3500", "4535"),
          doubleBook("000000001", "Monday", "2500", "2510"),
          doubleBook("000000001", "Monday", "2800", "2510"),
          doubleBook("000000002", "Monday", "3500", "4535"),
        ],
      },
      schedule: { complete: [], calendar: {}, total_exams: 0 },
    };
    // Only currentSchedule is read by the conflict hook.
    const state = { currentSchedule } as unknown as Parameters<
      Parameters<typeof useSchedulesStore>[0]
    >[0];
    vi.mocked(useSchedulesStore).mockImplementation((selector) =>
      selector(state),
    );
  });

  it("renders one row per student listing all of their conflicting exams", () => {
    render(<ConflictView />);

    const table = screen.getByRole("table");
    expect(
      within(table)
        .getAllByRole("columnheader")
        .map((th) => th.textContent),
    ).toEqual(["NUId", "Conflicts", "Conflicting exams"]);

    const [, ...bodyRows] = within(table).getAllByRole("row");
    expect(bodyRows).toHaveLength(2);

    const cells = bodyRows.map((row) =>
      within(row)
        .getAllByRole("cell")
        .map((td) => td.textContent),
    );
    expect(cells[0].slice(0, 2)).toEqual(["000000001", "2"]);
    expect(
      within(bodyRows[0])
        .getAllByRole("listitem")
        .map((li) => li.textContent),
    ).toEqual([
      "Monday 9AM-11AM: CS 2500 (2500), CS 2510 (2510), CS 2800 (2800)",
      "Tuesday 9AM-11AM: CS 3500 (3500), CS 4535 (4535)",
    ]);
    expect(cells[1]).toEqual([
      "000000002",
      "1",
      "Monday 9AM-11AM: CS 3500 (3500), CS 4535 (4535)",
    ]);

    expect(screen.getByText("Showing 1-2 of 2 students")).toBeDefined();
  });
  it("counts students, not conflict records, in the Student Conflicts card", () => {
    render(<ConflictView />);

    const card = screen
      .getByText("Student Conflicts")
      .closest<HTMLElement>('[data-slot="card"]');
    expect(card).not.toBeNull();
    expect(
      within(card as HTMLElement).getByText("Students with overlapping exams")
        .previousSibling?.textContent,
    ).toBe("2");
  });
});
