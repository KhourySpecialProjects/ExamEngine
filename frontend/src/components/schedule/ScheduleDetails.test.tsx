import { describe, expect, it } from "vitest";
import type { ScheduleSettings } from "@/lib/api/schedules";
import { type GenerationSetting, generationSettings } from "./ScheduleDetails";

const byLabel = (settings: GenerationSetting[]) =>
  Object.fromEntries(settings.map((s) => [s.label, s]));

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

describe("generationSettings", () => {
  it("marks settings an older run didn't record", () => {
    const settings = byLabel(
      generationSettings({
        settings: {
          ...recorded,
          blocks_per_day: 5,
          max_days: null,
          avoid_back_to_back: null,
        },
        settings_assumed: ["blocks_per_day"],
      }),
    );

    expect(settings["Exam blocks per day"]).toMatchObject({
      value: "5",
      note: expect.stringContaining("Not recorded"),
    });
    expect(settings["Max exam days"].value).toBe("Not recorded");
    expect(settings["Avoid back-to-back"].value).toBe("Not recorded");
  });

  it("shows optimization time only for the optimized algorithm", () => {
    const optimized = byLabel(
      generationSettings({
        settings: { ...recorded, algorithm: "annealing" },
        settings_assumed: [],
      }),
    );
    const classic = byLabel(
      generationSettings({ settings: recorded, settings_assumed: [] }),
    );

    expect(optimized.Algorithm.value).toBe("Optimized (annealing)");
    expect(optimized["Optimization time"].value).toBe("30s");
    expect(classic.Algorithm.value).toBe("Classic (DSATUR)");
    expect(classic["Optimization time"]).toBeUndefined();
    expect(classic["Exam blocks per day"].note).toBeUndefined();
  });

  it("flags back-to-back as unused by Classic", () => {
    const classic = byLabel(
      generationSettings({ settings: recorded, settings_assumed: [] }),
    );
    const optimized = byLabel(
      generationSettings({
        settings: {
          ...recorded,
          algorithm: "annealing",
          avoid_back_to_back: false,
        },
        settings_assumed: [],
      }),
    );

    expect(classic["Avoid back-to-back"].note).toBe("Not used by Classic");
    expect(optimized["Avoid back-to-back"]).toEqual({
      label: "Avoid back-to-back",
      value: "No",
      note: undefined,
    });
  });
});
