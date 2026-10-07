import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import type {
  ConflictMetric,
  ExamIssue,
  ScheduleSummary,
} from "@/lib/api/schedules";
import { useSchedulesStore } from "@/lib/store/schedulesStore";
import { makeCapacityBins } from "@/test/summary";
import { StatisticsView } from "./StatisticsView";

vi.mock("@/lib/store/schedulesStore", () => ({
  useSchedulesStore: vi.fn(),
}));

beforeAll(() => {
  global.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
});

const METRICS: ConflictMetric[] = [
  "student_double_book",
  "instructor_double_book",
  "student_over_daily_limit",
  "instructor_over_daily_limit",
  "student_back_to_back",
  "instructor_back_to_back",
  "large_courses_late",
];

const issue = (crn: string, size = 30): ExamIssue => ({
  crn,
  course: `CS ${crn}`,
  size,
});

/** A server summary of a schedule with nothing wrong, then the overrides. */
function summary(overrides: Partial<ScheduleSummary> = {}): ScheduleSummary {
  const noGroup = { groups: 0, sections: 0, students: 0 };
  return {
    settings: {
      algorithm: "dsatur",
      blocks_per_day: 5,
      time_budget_seconds: null,
      max_days: 7,
      student_max_per_day: 3,
      instructor_max_per_day: 3,
      avoid_back_to_back: true,
      prioritize_large_courses: false,
      promote_rooms: false,
    },
    settings_assumed: [],
    settings_unused: [],
    unique_students: 120,
    exams: {
      total: 2,
      placed: 2,
      unscheduled: 0,
      unroomed: 0,
      over_capacity: 0,
    },
    unscheduled: { exams: [], students: 0, groups: [], other_crns: [] },
    unroomed: { exams: [], students: 0 },
    over_capacity: [],
    conflicts: Object.fromEntries(
      METRICS.map((m) => [m, { people: 0, instances: 0 }]),
    ) as ScheduleSummary["conflicts"],
    rooms: {
      used: 2,
      uses: 2,
      average_fill: 75,
      fill_buckets: {
        under_50: 0,
        from_50_to_75: 0,
        from_75_to_90: 2,
        from_90_to_100: 0,
      },
      by_capacity: makeCapacityBins(),
    },
    calendar: {
      slots_used: 2,
      days_used: 2,
      days: [
        { day: "Monday", exams: 1, seats: 30 },
        { day: "Tuesday", exams: 1, seats: 30 },
      ],
      blocks: [{ label: "8AM-10AM", exams: 2 }],
      matrix: [[1], [1]],
    },
    groups: { combined: noGroup, common: noGroup },
    blockouts: { rooms: 0, slots: 0 },
    ...overrides,
  };
}

function mockSchedule(scheduleSummary: ScheduleSummary | null) {
  const currentSchedule = scheduleSummary && { summary: scheduleSummary };
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
    mockSchedule(summary());
    render(<StatisticsView />);

    expect(within(problems()).queryAllByRole("region")).toEqual([]);
    expect(problems().textContent).toContain(
      "Every exam has a time and a room that fits",
    );
  });

  it("lists problems before the overview: unscheduled, unroomed and over-capacity exams", () => {
    mockSchedule(
      summary({
        unscheduled: {
          exams: [issue("2")],
          students: 30,
          groups: [],
          other_crns: ["2"],
        },
        unroomed: { exams: [issue("3")], students: 30 },
        over_capacity: [{ ...issue("4", 419), room: "B", capacity: 400 }],
      }),
    );
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
      summary({
        unscheduled: {
          exams: [issue("2", 450)],
          students: 450,
          groups: [{ kind: "section", group: "2", reason, crns: ["2"] }],
          other_crns: [],
        },
      }),
    );
    render(<StatisticsView />);

    const card = within(problems()).getByRole("region", {
      name: "Unscheduled exams",
    });
    expect(card.textContent).toContain(`Section: CRN 2${reason}`);
    // The section explains its only CRN: no CRN list, no "other CRN" list.
    expect(card.textContent).not.toMatch(/\b1 (other )?CRN\b/);
  });

  it("shows the people in hard conflicts and links to the Conflicts tab", () => {
    const base = summary();
    mockSchedule(
      summary({
        conflicts: {
          ...base.conflicts,
          student_double_book: { people: 2, instances: 3 },
        },
      }),
    );
    const onShowConflicts = vi.fn();
    render(<StatisticsView onShowConflicts={onShowConflicts} />);

    const card = within(problems()).getByRole("region", {
      name: "Hard conflicts",
    });
    expect(card.textContent).toContain("Students double-booked2");
    expect(card.textContent).not.toContain("Instructors double-booked");
    fireEvent.click(
      within(card).getByRole("button", { name: "View conflicts" }),
    );
    expect(onShowConflicts).toHaveBeenCalledOnce();
  });

  it("reports exams scheduled out of all exams", () => {
    mockSchedule(
      summary({
        exams: {
          total: 3,
          placed: 2,
          unscheduled: 1,
          unroomed: 0,
          over_capacity: 0,
        },
      }),
    );
    render(<StatisticsView />);

    const overview = screen.getByRole("heading", { name: "Overview" })
      .parentElement as HTMLElement;
    expect(overview.textContent).toContain("2 / 3");
    expect(overview.textContent).toContain("66.7% have a day, time and room");
  });

  it("shows group and blockout cards only for what the dataset has", () => {
    mockSchedule(
      summary({
        groups: {
          combined: { groups: 1, sections: 2, students: 80 },
          common: { groups: 0, sections: 0, students: 0 },
        },
        blockouts: { rooms: 3, slots: 7 },
      }),
    );
    render(<StatisticsView />);

    const section = screen.getByRole("heading", {
      name: "Exam groups and room constraints",
    }).parentElement as HTMLElement;
    expect(section.textContent).toContain("Combined exams");
    expect(section.textContent).toContain("Room blockouts");
    expect(section.textContent).not.toContain("Common exams");
  });

  it("shows the large-only room and what this schedule placed in it", () => {
    mockSchedule(
      summary({
        large_only_room: {
          name: "Hall A",
          capacity: 500,
          cutoff: 275,
          exams: 4,
          sections: 6,
          students: 1400,
        },
      }),
    );
    render(<StatisticsView />);

    const section = screen.getByRole("heading", {
      name: "Exam groups and room constraints",
    }).parentElement as HTMLElement;
    expect(section.textContent).toContain("Large-only room: Hall A");
    const value = (label: string) =>
      within(section).getByText(label).nextSibling?.textContent;
    expect(value("Exams over 275")).toBe("4");
    expect(value("Students")).toBe("1,400");
    expect(value("Seats")).toBe("500");
  });

  it("shows no large-only room card when the dataset marks none", () => {
    mockSchedule(summary({ blockouts: { rooms: 1, slots: 1 } }));
    render(<StatisticsView />);

    expect(screen.queryByText(/Large-only room/)).toBeNull();
  });
});
