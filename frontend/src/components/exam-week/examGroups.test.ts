import { describe, expect, it } from "vitest";
import { buildExamGroups, withGroups } from "./examGroups";
import { doubleBookedSlots, examsBySlot, type WeekExam } from "./examWeek";

const exam = (crn: string): WeekExam => ({
  crn,
  course_code: `CS ${crn}`,
  day: 0,
  day_name: "Monday",
  block: 0,
  block_time: "9AM-11AM",
  room: "Hall",
});

describe("buildExamGroups", () => {
  it("pulls a whole combined exam into a common group one of its CRNs is in", () => {
    const groups = buildExamGroups(
      { "A Combined": ["1", " 2 "], "B Combined": ["5", "6"] },
      { "X Common": ["2", "3"] },
    );

    expect(withGroups(exam("1"), groups)).toMatchObject({
      combined: "A Combined",
      common: "X Common",
    });
    expect(withGroups(exam("5"), groups)).toMatchObject({
      combined: "B Combined",
      common: null,
    });
    expect(groups.commonCrns.get("X Common")?.sort()).toEqual(["1", "2", "3"]);
  });
});

describe("doubleBookedSlots", () => {
  const groups = buildExamGroups(
    { "A Combined": ["1", "2"] },
    { "X Common": ["3", "4"] },
  );
  const slots = (crns: string[]) =>
    doubleBookedSlots(
      examsBySlot(crns.map((crn) => withGroups(exam(crn), groups))),
    );

  it("counts the sections of one combined or common exam once", () => {
    expect(slots(["1", "2"]).size).toBe(0);
    expect(slots(["3", "4"]).size).toBe(0);
  });

  it("still flags two different exams in one block", () => {
    expect([...slots(["1", "3"])]).toEqual(["0-0"]);
    expect([...slots(["1", "9"])]).toEqual(["0-0"]);
  });
});
