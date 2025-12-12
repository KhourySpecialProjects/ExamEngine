import { render, screen } from "@testing-library/react";
import {
  beforeAll,
  beforeEach,
  describe,
  expect,
  it,
  type Mock,
  vi,
} from "vitest";
import { useSchedulesStore } from "@/lib/store/schedulesStore";
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

describe("StatisticsView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders placeholder when currentSchedule is null", () => {
    (useSchedulesStore as any).mockReturnValue(null);

    render(<StatisticsView />);

    expect(screen.getByText("Statistics Dashboard")).toBeDefined();
    expect(
      screen.getByText("Generate a schedule to view statistics"),
    ).toBeDefined();
  });

  it("renders statistics overview when schedule exists", () => {
    (useSchedulesStore as any).mockReturnValue({
      schedule: {
        complete: [
          { Day: "Monday", Block: "1", Size: 30, Capacity: 40 },
          { Day: "Monday", Block: "2", Size: 20, Capacity: 20 },
        ],
        total_exams: 2,
      },
      summary: {
        real_conflicts: 1,
        num_students: 200,
        num_rooms: 15,
        slots_used: 5,
        num_classes: 2,
      },
      conflicts: {
        total: 0,
        breakdown: [
          {
            conflict_type: "student_double_book",
            entity_id: "S123",
            day: "Monday",
            block_time: "8:00",
            course: "CS2000",
            conflicting_course: "CS3000",
            crn: "11111",
            conflicting_crn: "22222",
          },
        ],
      },
      currentSchedule: {
        schedule: {
          complete: [
            { Day: "Monday", Block: "1", Size: 30, Capacity: 40 },
            { Day: "Monday", Block: "2", Size: 20, Capacity: 20 },
          ],
          total_exams: 2,
        },
        summary: {
          real_conflicts: 1,
          num_students: 200,
          num_rooms: 15,
          slots_used: 5,
          num_classes: 2,
        },
        conflicts: {
          total: 0,
          breakdown: [
            {
              conflict_type: "student_double_book",
              entity_id: "S123",
              day: "Monday",
              block_time: "8:00",
              course: "CS2000",
              conflicting_course: "CS3000",
              crn: "11111",
              conflicting_crn: "22222",
            },
          ],
        },
      },
    });

    render(<StatisticsView />);

    expect(screen.getByText("Statistics View")).toBeDefined();
    expect(screen.getByText("Total Exams")).toBeDefined();
    expect(screen.getAllByText("2")).toBeDefined();
    expect(screen.getByText("Conflicts")).toBeDefined();
    expect(screen.getByText("1")).toBeDefined();
  });

  it("shows 'No exam data available' when studentsPerDayData is empty", () => {
    (useSchedulesStore as unknown as Mock).mockReturnValue({
      schedule: {
        complete: [],
        total_exams: 20,
      },
      summary: {
        real_conflicts: 3,
        num_students: 200,
        num_rooms: 15,
        slots_used: 5,
        num_classes: 2,
      },
      conflicts: {
        total: 0,
        breakdown: [
          {
            conflict_type: "student_double_book",
            entity_id: "S123",
            day: "Monday",
            block_time: "8:00",
            course: "CS2000",
            conflicting_course: "CS3000",
            crn: "11111",
            conflicting_crn: "22222",
          },
        ],
      },
      currentSchedule: {
        schedule: {
          complete: [],
          total_exams: 20,
        },
        summary: {
          real_conflicts: 3,
          num_students: 200,
          num_rooms: 15,
          slots_used: 5,
          num_classes: 2,
        },
        conflicts: {
          total: 0,
          breakdown: [
            {
              conflict_type: "student_double_book",
              entity_id: "S123",
              day: "Monday",
              block_time: "8:00",
              course: "CS2000",
              conflicting_course: "CS3000",
              crn: "11111",
              conflicting_crn: "22222",
            },
          ],
        },
      },
    });

    render(<StatisticsView />);

    expect(screen.getByText("No exam data available")).toBeDefined();
  });

  it("renders conflict placeholder when real_conflicts > 0 but breakdown is empty", () => {
    (useSchedulesStore as any).mockReturnValue({
      schedule: {
        complete: [
          { Day: "Monday", Block: "1", Size: 30, Capacity: 40 },
          { Day: "Monday", Block: "2", Size: 20, Capacity: 20 },
        ],
        total_exams: 2,
      },
      summary: {
        real_conflicts: 3,
        num_students: 200,
        num_rooms: 15,
        slots_used: 5,
        num_classes: 2,
      },
      conflicts: {
        total: 0,
        breakdown: [],
      },
      currentSchedule: {
        schedule: {
          complete: [
            { Day: "Monday", Block: "1", Size: 30, Capacity: 40 },
            { Day: "Monday", Block: "2", Size: 20, Capacity: 20 },
          ],
          total_exams: 2,
        },
        summary: {
          real_conflicts: 3,
          num_students: 200,
          num_rooms: 15,
          slots_used: 5,
          num_classes: 2,
        },
        conflicts: {
          total: 0,
          breakdown: [],
        },
      },
    });

    render(<StatisticsView />);

    expect(
      screen.getByText(/Analytics and insights about your exam schedule/i),
    ).toBeDefined();

    expect(screen.getByText(/Statistics View/i)).toBeDefined();
  });
});
