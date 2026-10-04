import { describe, expect, it } from "vitest";
import {
  CLASSIC_SETTINGS as classic,
  makeSummary as summary,
} from "@/test/summary";
import {
  addColumn,
  calendarShape,
  columnOrder,
  compareIds,
  compareSettings,
  delta,
  formatDelta,
  isScheduleId,
  moveColumn,
  publishBlockers,
  reorderColumn,
  setBaseline,
} from "./compare";

const A = "0b6f1c1e-0000-4000-8000-00000000000a";
const B = "0b6f1c1e-0000-4000-8000-00000000000b";
const C = "0b6f1c1e-0000-4000-8000-00000000000c";
const D = "0b6f1c1e-0000-4000-8000-00000000000d";
const E = "0b6f1c1e-0000-4000-8000-00000000000e";

describe("URL rules", () => {
  it("keeps URL order, drops blanks and repeats, and uses only the first 4", () => {
    expect(compareIds([B, "", A, B.toUpperCase(), C, D, E])).toEqual([
      B,
      A,
      C,
      D,
    ]);
    expect(compareIds(null)).toEqual([]);
  });

  it("shows the first available column first, as the baseline", () => {
    const all = () => true;
    const notA = (id: string) => id !== A;
    const none = () => false;

    expect(columnOrder([A, B, C], all)).toEqual([A, B, C]);
    expect(columnOrder([A, B, C], notA)).toEqual([B, A, C]);
    expect(columnOrder([A, B], none)).toEqual([A, B]);
  });

  it("sets a baseline by moving it to the front, keeping the others' order", () => {
    expect(setBaseline([A, B, C, D], C)).toEqual([C, A, B, D]);
    expect(setBaseline([A, B], A)).toEqual([A, B]);
    // An old `base=` naming a schedule not in `ids` changes nothing.
    expect(setBaseline([A, B], E)).toEqual([A, B]);
  });

  it("only asks the server about ids that look like schedule ids", () => {
    expect(isScheduleId(A)).toBe(true);
    expect(isScheduleId("not-a-schedule")).toBe(false);
  });

  it("moves a column one place, never onto or off the baseline", () => {
    expect(moveColumn([A, B, C], C, -1)).toEqual([A, C, B]);
    expect(moveColumn([A, B, C], B, 1)).toEqual([A, C, B]);
    expect(moveColumn([A, B, C], B, -1)).toEqual([A, B, C]);
    expect(moveColumn([A, B, C], A, 1)).toEqual([A, B, C]);
    expect(moveColumn([A, B, C], C, 1)).toEqual([A, B, C]);
  });

  it("drops a dragged column in the target's place, never passing the baseline", () => {
    expect(reorderColumn([A, B, C, D], B, D)).toEqual([A, C, D, B]);
    expect(reorderColumn([A, B, C, D], D, B)).toEqual([A, D, B, C]);
    expect(reorderColumn([A, B, C, D], C, A)).toEqual([A, B, C, D]);
    expect(reorderColumn([A, B, C, D], A, C)).toEqual([A, B, C, D]);
  });

  it("adds a column last, never twice and never past 4", () => {
    expect(addColumn([A, B], C)).toEqual([A, B, C]);
    expect(addColumn([A, B], A)).toEqual([A, B]);
    expect(addColumn([A, B, C, D], E)).toEqual([A, B, C, D]);
  });
});

describe("difference from the baseline", () => {
  it("colours a lower count as better", () => {
    expect(delta(3, 5)).toEqual({ value: -2, tone: "better" });
    expect(delta(7, 5)).toEqual({ value: 2, tone: "worse" });
    expect(delta(5, 5)).toEqual({ value: 0, tone: "same" });
  });

  it("formats with a sign", () => {
    expect(formatDelta(1234)).toBe("+1,234");
    expect(formatDelta(-2)).toBe("−2");
    expect(formatDelta(0)).toBe("±0");
  });
});

describe("compareSettings", () => {
  it("splits settings into those that differ and those the same in all", () => {
    const { differing, same } = compareSettings([
      summary(),
      summary({ settings: { ...classic, max_days: 5 } }),
    ]);

    expect(differing.map((s) => s.label)).toEqual(["Max exam days"]);
    expect(differing[0].rows.map((r) => r.value)).toEqual(["7", "5"]);
    expect(same.map((s) => s.label)).toContain("Algorithm");
    expect(same).toHaveLength(7);
  });

  it("treats a setting one algorithm ignores as different from a used one", () => {
    const optimized = summary({
      settings: { ...classic, algorithm: "annealing" },
      settings_unused: ["prioritize_large_courses"],
    });

    const { differing } = compareSettings([summary(), optimized]);
    const time = differing.find((s) => s.key === "time_budget_seconds");

    // Both runs stored 15 s, but Classic doesn't use it.
    expect(time?.rows.map((r) => r.value)).toEqual([
      "Not used by Classic",
      "15s",
    ]);
    expect(differing.map((s) => s.key)).toEqual([
      "algorithm",
      "time_budget_seconds",
      "avoid_back_to_back",
      "prioritize_large_courses",
    ]);
  });

  it("compares shown values, so an assumed value equals the recorded one", () => {
    const { differing } = compareSettings([
      summary({ settings_assumed: ["blocks_per_day"] }),
      summary(),
    ]);

    expect(differing).toEqual([]);
  });
});

describe("publishBlockers", () => {
  it("is empty for a publishable schedule", () => {
    expect(publishBlockers(summary())).toEqual([]);
  });

  it("lists every failing count, adding up the hard conflict types", () => {
    const base = summary();
    const blockers = publishBlockers(
      summary({
        exams: { ...base.exams, unscheduled: 2, over_capacity: 1 },
        conflicts: {
          ...base.conflicts,
          student_double_book: { people: 3, instances: 4 },
          instructor_over_daily_limit: { people: 1, instances: 1 },
          // Soft: doesn't block publishing.
          student_back_to_back: { people: 9, instances: 9 },
        },
      }),
    );

    expect(blockers).toEqual([
      { label: "with hard conflicts", count: 4 },
      { label: "unscheduled", count: 2 },
      { label: "over capacity", count: 1 },
    ]);
  });
});

describe("calendarShape", () => {
  it("puts every schedule on the same days, blocks and scale", () => {
    const shape = calendarShape([
      summary({
        calendar: {
          slots_used: 2,
          days_used: 1,
          days: [{ day: "Tuesday", exams: 4, seats: 40 }],
          blocks: [
            { label: "2PM-4PM", exams: 3 },
            { label: "7PM-9PM", exams: 1 },
          ],
          matrix: [[3, 1]],
        },
      }),
      summary({
        calendar: {
          slots_used: 2,
          days_used: 2,
          days: [
            { day: "Monday", exams: 6, seats: 60 },
            { day: "Tuesday", exams: 1, seats: 10 },
          ],
          blocks: [
            { label: "9AM-11AM", exams: 2 },
            { label: "11:30AM-1:30PM", exams: 5 },
          ],
          matrix: [
            [2, 4],
            [0, 1],
          ],
        },
      }),
    ]);

    expect(shape.days).toEqual(["Monday", "Tuesday"]);
    expect(shape.blocks).toEqual([
      "9AM-11AM",
      "11:30AM-1:30PM",
      "2PM-4PM",
      "7PM-9PM",
    ]);
    expect(shape.schedules[0]).toEqual({
      days: [0, 4],
      blocks: [0, 0, 3, 1],
      matrix: [
        [0, 0, 0, 0],
        [0, 0, 3, 1],
      ],
    });
    expect(shape.schedules[1].matrix).toEqual([
      [2, 4, 0, 0],
      [0, 1, 0, 0],
    ]);
    expect([shape.maxDay, shape.maxBlock, shape.maxCell]).toEqual([6, 5, 4]);
  });
});
