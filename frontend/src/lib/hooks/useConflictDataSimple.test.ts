import { describe, expect, it } from "vitest";
import type { ConflictBreakdown, ScheduleExam } from "../api/schedules";
import {
  buildConflictRows,
  type PersonConflictRow,
} from "./useConflictDataSimple";

const doubleBook = (
  student: string,
  day: string,
  block: number,
  crn: string,
  conflictingCrn: string,
): ConflictBreakdown => ({
  conflict_type: "student_double_book",
  entity_id: student,
  day,
  block,
  block_time: ["9AM-11AM", "11:30AM-1:30PM", "2PM-4PM"][block],
  crn,
  course: `CS ${crn}`,
  conflicting_crn: conflictingCrn,
  conflicting_course: `CS ${conflictingCrn}`,
});

const personRows = (
  breakdown: ConflictBreakdown[],
  examsByCrn = new Map<string, ScheduleExam>(),
) =>
  buildConflictRows(breakdown, examsByCrn).filter(
    (r): r is PersonConflictRow => r.kind === "person",
  );

describe("buildConflictRows", () => {
  it("collapses a 2-course double-book into one row listing both courses", () => {
    const rows = personRows([doubleBook("000000001", "Monday", 0, "2", "1")]);

    expect(rows).toHaveLength(1);
    expect(rows[0].entity).toBe("000000001");
    expect(rows[0].conflictCount).toBe(1);
    expect(rows[0].instances).toEqual([
      {
        day: "Monday",
        time: "9AM-11AM",
        slots: ["9AM-11AM"],
        courses: [
          { course: "CS 1", crn: "1" },
          { course: "CS 2", crn: "2" },
        ],
      },
    ]);
  });

  it("merges a 3-course double-book (several records, same slot) into one instance", () => {
    const rows = personRows([
      doubleBook("000000001", "Monday", 0, "2", "1"),
      doubleBook("000000001", "Monday", 0, "3", "1"),
    ]);

    expect(rows).toHaveLength(1);
    expect(rows[0].conflictCount).toBe(1);
    expect(rows[0].instances[0].courses.map((c) => c.crn)).toEqual([
      "1",
      "2",
      "3",
    ]);
  });

  it("lists one student's conflicts on different days chronologically in one row", () => {
    const rows = personRows([
      doubleBook("000000001", "Wednesday", 0, "4", "3"),
      doubleBook("000000001", "Monday", 2, "2", "1"),
      doubleBook("000000001", "Monday", 0, "6", "5"),
    ]);

    expect(rows).toHaveLength(1);
    expect(rows[0].conflictCount).toBe(3);
    expect(rows[0].instances.map((i) => `${i.day} ${i.time}`)).toEqual([
      "Monday 9AM-11AM",
      "Monday 2PM-4PM",
      "Wednesday 9AM-11AM",
    ]);
  });

  it("keeps different students (and IDs differing only by leading zeros) apart", () => {
    const rows = personRows([
      doubleBook("000000001", "Monday", 0, "2", "1"),
      doubleBook("1", "Monday", 0, "2", "1"),
      doubleBook("000000001", "Tuesday", 0, "4", "3"),
    ]);

    expect(rows.map((r) => [r.entity, r.conflictCount])).toEqual([
      ["000000001", 2],
      ["1", 1],
    ]);
  });

  it("does not merge person records that have no entity", () => {
    const orphan = {
      ...doubleBook("", "Monday", 0, "2", "1"),
      entity_id: null,
    };
    const rows = personRows([orphan, orphan]);

    expect(rows).toHaveLength(2);
    expect(rows.every((r) => r.entity === "" && r.conflictCount === 1)).toBe(
      true,
    );
  });

  it("groups back-to-back by instructor using block times as slots, without courses", () => {
    const record = (day: string, blocks: number[], times: string[]) => ({
      conflict_type: "back_to_back_instructor",
      entity_id: "Dr. Smith",
      student_id: null,
      day,
      blocks,
      block_times: times,
    });
    const rows = personRows([
      record("Tuesday", [0, 1], ["9AM-11AM", "11:30AM-1:30PM"]),
      record("Monday", [1, 2], ["11:30AM-1:30PM", "2PM-4PM"]),
    ]);

    expect(rows).toHaveLength(1);
    expect(rows[0].entity).toBe("Dr. Smith");
    expect(rows[0].instances).toEqual([
      {
        day: "Monday",
        time: "11:30AM-1:30PM, 2PM-4PM",
        slots: ["11:30AM-1:30PM", "2PM-4PM"],
        courses: [],
      },
      {
        day: "Tuesday",
        time: "9AM-11AM, 11:30AM-1:30PM",
        slots: ["9AM-11AM", "11:30AM-1:30PM"],
        courses: [],
      },
    ]);
  });

  it("fills missing course codes and exam details from the schedule by CRN", () => {
    const exam = (crn: string, course: string): ScheduleExam => ({
      CRN: crn,
      Course: course,
      Day: "Friday",
      Block: "1",
      Room: "WVH 210",
      Capacity: 100,
      Size: 40,
      Valid: true,
    });
    const math = exam("10", "MATH 1341");
    const phys = exam("11", "PHYS 1151");
    const rows = personRows(
      [
        {
          conflict_type: "student_gt_max_per_day",
          entity_id: "000000007",
          student_id: "000000007",
          day: "Friday",
          block: 1,
          block_time: "11:30AM-1:30PM",
          crn: "10",
          course: "Unknown",
          conflicting_crns: ["11"],
          conflicting_courses: ["Unknown"],
        },
      ],
      new Map([
        ["10", math],
        ["11", phys],
      ]),
    );

    expect(rows[0].instances[0].courses).toEqual([
      { course: "MATH 1341", crn: "10", exam: math },
      { course: "PHYS 1151", crn: "11", exam: phys },
    ]);
  });

  it("keeps large_course_not_early as one row per course record", () => {
    const large = (crn: string): ConflictBreakdown => ({
      conflict_type: "large_course_not_early",
      crn,
      course: `BIG ${crn}`,
      size: 250,
      day: "Friday",
      block: 2,
      block_time: "2PM-4PM",
    });

    expect(buildConflictRows([large("1"), large("2")], new Map())).toEqual([
      {
        kind: "record",
        id: "conflict-0",
        type: "large_course_not_early",
        entity: "",
        day: "Friday",
        block: "2",
        course: "BIG 1",
        crn: "1",
        size: 250,
      },
      {
        kind: "record",
        id: "conflict-1",
        type: "large_course_not_early",
        entity: "",
        day: "Friday",
        block: "2",
        course: "BIG 2",
        crn: "2",
        size: 250,
      },
    ]);
  });
});
