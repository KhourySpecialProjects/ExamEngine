import { describe, expect, it } from "vitest";
import type { ScheduleSettings } from "@/lib/api/schedules";
import { type SettingRow, settingRows } from "./scheduleSettings";

const byLabel = (rows: SettingRow[]) =>
  Object.fromEntries(rows.map((row) => [row.label, row]));

const recorded: ScheduleSettings = {
  algorithm: "dsatur",
  blocks_per_day: 4,
  time_budget_seconds: 30,
  max_days: 7,
  student_max_per_day: 2,
  instructor_max_per_day: 1,
  avoid_back_to_back: true,
  prioritize_large_courses: true,
};

describe("settingRows", () => {
  it("marks settings an older run didn't record", () => {
    const rows = byLabel(
      settingRows({
        settings: {
          ...recorded,
          blocks_per_day: 5,
          max_days: null,
          prioritize_large_courses: null,
        },
        settings_assumed: ["blocks_per_day"],
        settings_unused: [],
      }),
    );

    expect(rows["Exam blocks per day"]).toMatchObject({
      value: "5",
      note: expect.stringContaining("Not recorded"),
    });
    expect(rows["Max exam days"].value).toBe("Not recorded");
    expect(rows["Prioritize large classes"].value).toBe("Not recorded");
    expect(rows["Max exam days"].note).toBeUndefined();
  });

  it("names the algorithm that ignores a setting instead of its stored value", () => {
    const classic = byLabel(
      settingRows({
        settings: recorded,
        settings_assumed: [],
        settings_unused: ["time_budget_seconds", "avoid_back_to_back"],
      }),
    );
    const optimized = byLabel(
      settingRows({
        settings: { ...recorded, algorithm: "annealing" },
        settings_assumed: [],
        settings_unused: ["prioritize_large_courses"],
      }),
    );

    expect(classic.Algorithm.value).toBe("Classic (DSATUR)");
    expect(classic["Optimization time"]).toMatchObject({
      value: "Not used by Classic",
      unused: true,
    });
    expect(classic["Avoid back-to-back"].value).toBe("Not used by Classic");
    expect(classic["Prioritize large classes"]).toMatchObject({
      value: "Yes",
      unused: false,
    });
    expect(optimized.Algorithm.value).toBe("Optimized (annealing)");
    expect(optimized["Optimization time"].value).toBe("30s");
    expect(optimized["Prioritize large classes"]).toMatchObject({
      value: "Always on in Optimized",
      unused: true,
    });
  });
});
