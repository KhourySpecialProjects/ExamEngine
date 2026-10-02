import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import type {
  ConflictBreakdown,
  ScheduleExam,
  UnscheduledGroup,
} from "@/lib/api/schedules";
import { useSchedulesStore } from "@/lib/store/schedulesStore";
import { StatisticsView } from "./StatisticsView";

vi.mock("@/lib/store/schedulesStore", () => ({
  useSchedulesStore: vi.fn(),
}));
// Group hooks fetch from the API; these tests have no groups.
vi.mock("@/lib/hooks/useCourseMerges", () => ({
  useCourseMerges: () => ({ merges: {}, isMerged: () => false }),
}));
vi.mock("@/lib/hooks/useCommonExams", () => ({
  useCommonExams: () => ({ commonGroups: {}, isCommon: () => false }),
}));

beforeAll(() => {
  global.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
});

const exam = (
  crn: string,
  day: string,
  room: string,
  size = 30,
  capacity = 40,
): ScheduleExam => ({
  CRN: crn,
  Course: `CS ${crn}`,
  Day: day,
  Block: day ? "9AM-11AM" : "",
  Room: room,
  Capacity: room ? capacity : 0,
  Size: size,
  Valid: true,
});

function mockSchedule(
  complete: ScheduleExam[] | null,
  breakdown: ConflictBreakdown[] = [],
  unscheduledGroups: UnscheduledGroup[] = [],
) {
  const currentSchedule = complete && {
    dataset_id: "d1",
    schedule: { complete, calendar: {}, total_exams: complete.length },
    conflicts: { total: breakdown.length, details: {}, breakdown },
    unscheduled_groups: unscheduledGroups,
  };
  const state = { currentSchedule } as unknown as Parameters<
    Parameters<typeof useSchedulesStore>[0]
  >[0];
  vi.mocked(useSchedulesStore).mockImplementation((selector) =>
    selector(state),
  );
}

const problems = () =>
  screen.getByRole("heading", { name: "Needs attention" })
    .parentElement as HTMLElement;

describe("StatisticsView", () => {
  beforeEach(() => vi.clearAllMocks());

  it("asks for a schedule when there is none", () => {
    mockSchedule(null);
    render(<StatisticsView />);

    expect(
      screen.getByText("Generate a schedule to view statistics"),
    ).toBeTruthy();
  });

  it("says nothing needs attention when every exam is placed and there are no hard conflicts", () => {
    mockSchedule([exam("1", "Monday", "A"), exam("2", "Tuesday", "B")]);
    render(<StatisticsView />);

    expect(within(problems()).queryAllByRole("region")).toEqual([]);
    expect(problems().textContent).toContain(
      "Every exam has a time and a room that fits",
    );
  });

  it("lists problems before the overview: unscheduled, unroomed and over-capacity exams", () => {
    mockSchedule([
      exam("1", "Monday", "A"),
      exam("2", "", ""),
      exam("3", "Monday", ""),
      exam("4", "Tuesday", "B", 419, 400),
    ]);
    render(<StatisticsView />);

    const cards = within(problems()).getAllByRole("region");
    expect(cards.map((c) => c.getAttribute("aria-label"))).toEqual([
      "Unscheduled exams",
      "Exams without a room",
      "Rooms over capacity",
    ]);
    expect(cards[2].textContent).toContain("419/400 in B");
    const headings = screen
      .getAllByRole("heading", { level: 2 })
      .map((h) => h.textContent);
    expect(headings.indexOf("Needs attention")).toBeLessThan(
      headings.indexOf("Overview"),
    );
  });

  it("names an unscheduled section by CRN with the scheduler's reason", () => {
    const reason = "450 students; largest room seats 400";
    mockSchedule(
      [exam("1", "Monday", "A"), exam("2", "", "", 450)],
      [],
      [{ kind: "section", group: "2", reason, crns: ["2"] }],
    );
    render(<StatisticsView />);

    const card = within(problems()).getByRole("region", {
      name: "Unscheduled exams",
    });
    expect(card.textContent).toContain(`Section: CRN 2${reason}`);
    // The section explains its only CRN: no CRN list, no "other CRN" list.
    expect(card.textContent).not.toMatch(/\b1 (other )?CRN\b/);
  });

  it("counts people in hard conflicts like the Conflicts tab and links to it", () => {
    const doubleBook = (student: string, crn: string): ConflictBreakdown => ({
      conflict_type: "student_double_book",
      entity_id: student,
      day: "Monday",
      block: 0,
      block_time: "9AM-11AM",
      crn,
      course: `CS ${crn}`,
      conflicting_crn: "9",
      conflicting_course: "CS 9",
    });
    // Two records for one student (3-way double-book) + one other student.
    mockSchedule(
      [exam("1", "Monday", "A")],
      [doubleBook("001", "1"), doubleBook("001", "2"), doubleBook("002", "1")],
    );
    const onShowConflicts = vi.fn();
    render(<StatisticsView onShowConflicts={onShowConflicts} />);

    const card = within(problems()).getByRole("region", {
      name: "Hard conflicts",
    });
    expect(card.textContent).toContain("Students double-booked2");
    fireEvent.click(
      within(card).getByRole("button", { name: "View conflicts" }),
    );
    expect(onShowConflicts).toHaveBeenCalledOnce();
  });

  it("reports exams scheduled out of all exams", () => {
    mockSchedule([exam("1", "Monday", "A"), exam("2", "", "")]);
    render(<StatisticsView />);

    const overview = screen.getByRole("heading", { name: "Overview" })
      .parentElement as HTMLElement;
    expect(overview.textContent).toContain("1 / 2");
    expect(overview.textContent).toContain("50% have a day, time and room");
  });
});
