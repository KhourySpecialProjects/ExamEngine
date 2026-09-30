import { describe, expect, it } from "vitest";
import type { ScheduleExam } from "@/lib/api/schedules";
import {
  computeScheduleStats,
  type ScheduleStatsInput,
} from "./useScheduleStats";

const exam = (
  crn: string,
  day: string,
  block: string,
  room: string,
  size: number,
  capacity: number,
): ScheduleExam => ({
  CRN: crn,
  Course: `CS ${crn}`,
  Day: day,
  Block: block,
  Room: room,
  Capacity: capacity,
  Size: size,
  Valid: true,
});

const stats = (
  exams: ScheduleExam[],
  overrides: Partial<ScheduleStatsInput> = {},
) =>
  computeScheduleStats({
    exams,
    uniqueStudents: null,
    unscheduledGroups: [],
    combinedGroupCount: 0,
    isCombined: () => false,
    commonGroupCount: 0,
    isCommon: () => false,
    ...overrides,
  });

describe("computeScheduleStats", () => {
  it("splits exams into placed, unscheduled (no day) and unroomed (day, no room)", () => {
    const s = stats([
      exam("1", "Monday", "9AM-11AM", "WVH 210", 40, 50),
      exam("2", "", "", "", 120, 0),
      exam("3", "Monday", "11:30AM-1:30PM", "", 30, 0),
    ]);

    expect(s.totalExams).toBe(3);
    expect(s.placedExams).toBe(1);
    expect(s.unscheduled.exams.map((e) => e.crn)).toEqual(["2"]);
    expect(s.unscheduled.students).toBe(120);
    expect(s.unroomed.exams.map((e) => e.crn)).toEqual(["3"]);
    expect(s.unroomed.students).toBe(30);
    // An unroomed exam still occupies its slot; an unscheduled one doesn't.
    expect(s.slotsUsed).toBe(2);
    expect(s.roomsUsed).toBe(1);
  });

  it("flags exams in rooms smaller than their enrollment, worst first, and caps utilization at 100% per exam", () => {
    const s = stats([
      exam("1", "Monday", "9AM-11AM", "A", 50, 100),
      exam("2", "Monday", "9AM-11AM", "B", 419, 400),
      exam("3", "Tuesday", "9AM-11AM", "C", 150, 100),
    ]);

    expect(s.overCapacity.map((e) => [e.crn, e.size, e.capacity])).toEqual([
      ["3", 150, 100],
      ["2", 419, 400],
    ]);
    // (50% + 100% + 100%) / 3
    expect(s.roomUtilization).toBe(83.3);
  });

  it("orders days Monday..Sunday and blocks by number or by start time", () => {
    const saved = stats([
      exam("1", "Wednesday", "2PM-4PM", "A", 10, 20),
      exam("2", "Monday", "11:30AM-1:30PM", "A", 10, 20),
      exam("3", "Monday", "9AM-11AM", "B", 10, 20),
      exam("4", "Saturday", "7PM-9PM", "A", 10, 20),
      exam("5", "Tuesday", "4:30PM-6:30PM", "A", 10, 20),
    ]);
    expect(saved.perDay.map((d) => [d.name, d.exams, d.students])).toEqual([
      ["Monday", 2, 20],
      ["Tuesday", 1, 10],
      ["Wednesday", 1, 10],
      ["Saturday", 1, 10],
    ]);
    expect(saved.perBlock.map((b) => b.name)).toEqual([
      "9AM-11AM",
      "11:30AM-1:30PM",
      "2PM-4PM",
      "4:30PM-6:30PM",
      "7PM-9PM",
    ]);

    const generated = stats([
      exam("1", "Monday", "10 (7PM-9PM)", "A", 1, 2),
      exam("2", "Monday", "2 (2PM-4PM)", "A", 1, 2),
    ]);
    expect(generated.perBlock.map((b) => b.name)).toEqual([
      "2 (2PM-4PM)",
      "10 (7PM-9PM)",
    ]);
  });

  it("lists only unscheduled CRNs that no reported group explains", () => {
    const s = stats(
      [exam("1", "", "", "", 10, 0), exam("2", "", "", "", 10, 0)],
      {
        unscheduledGroups: [
          { kind: "combined", group: "G", reason: "too big", crns: ["1"] },
        ],
      },
    );

    expect(s.unscheduled.otherCrns).toEqual(["2"]);
  });

  it("counts scheduled sections and students in combined and common groups", () => {
    const s = stats(
      [
        exam("1", "Monday", "9AM-11AM", "A", 30, 100),
        exam("2", "Monday", "9AM-11AM", "A", 20, 100),
        exam("3", "Monday", "9AM-11AM", "B", 5, 100),
      ],
      {
        combinedGroupCount: 1,
        isCombined: (crn) => crn === "1" || crn === "2",
        commonGroupCount: 1,
        isCommon: (crn) => crn !== "3",
      },
    );

    expect(s.combined).toEqual({ groups: 1, sections: 2, students: 50 });
    expect(s.common).toEqual({ groups: 1, sections: 2, students: 50 });
  });
});
