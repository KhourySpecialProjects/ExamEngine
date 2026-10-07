import { render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { CalendarExam } from "@/lib/api/schedules";
import { useSchedulesStore } from "@/lib/store/schedulesStore";
import { makeLateAddition, makeSchedule } from "@/test/summary";
import ListView from "./ListView";

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    datasets: {
      getCourseMerges: vi.fn().mockResolvedValue({}),
      getCommonExams: vi.fn().mockResolvedValue({}),
    },
  },
}));

const exam = (crn: string, course: string): CalendarExam => ({
  CRN: crn,
  Course: course,
  Room: "Hall A",
  Capacity: 100,
  Size: 30,
  Valid: true,
  Instructor: "I-1",
});

beforeEach(() => {
  vi.spyOn(console, "log").mockImplementation(() => {});
});

describe("ListView", () => {
  it("marks only the late-added exams", () => {
    useSchedulesStore.setState({
      currentSchedule: makeSchedule({
        schedule: {
          complete: [],
          calendar: {
            Monday: {
              "8AM-10AM": [exam("90001", "CS 1000"), exam("100", "CS 2000")],
            },
          },
          total_exams: 2,
        },
        lineage: {
          based_on: { id: "s1", name: "Fall", available: true },
          original: { id: "s1", name: "Fall", available: true },
          late_additions: [makeLateAddition({ crn: "90001" })],
          newer_versions: [],
        },
      }),
    });
    render(<ListView />);

    const row = (course: string) =>
      screen.getByText(course).closest("tr") as HTMLElement;
    expect(within(row("CS 1000")).getByText("Late add")).toBeTruthy();
    expect(within(row("CS 2000")).queryByText("Late add")).toBeNull();
  });
});
