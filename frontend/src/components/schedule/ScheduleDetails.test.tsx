import { describe, expect, it } from "vitest";
import { type GenerationSetting, generationSettings } from "./ScheduleDetails";

const byLabel = (settings: GenerationSetting[]) =>
  Object.fromEntries(settings.map((s) => [s.label, s]));

describe("generationSettings", () => {
  it("fills in what runs from before the newer options actually used", () => {
    // Stored shape of a run generated before blocks_per_day and algorithm
    // were recorded.
    const settings = byLabel(
      generationSettings({
        algorithm: "DSATUR",
        parameters: {
          max_days: 7,
          avoid_back_to_back: true,
          student_max_per_day: 2,
          instructor_max_per_day: 1,
          prioritize_large_courses: true,
        },
      }),
    );

    expect(settings.Algorithm.value).toBe("Classic (DSATUR)");
    expect(settings["Exam blocks per day"]).toMatchObject({
      value: "5",
      note: expect.stringContaining("Not recorded"),
    });
    expect(settings["Optimization time"]).toBeUndefined();
  });

  it("shows optimization time only for the optimized algorithm", () => {
    const optimized = byLabel(
      generationSettings({
        algorithm: "Annealing",
        parameters: { algorithm: "annealing", time_budget_seconds: 30 },
      }),
    );
    const classic = byLabel(
      generationSettings({
        algorithm: "DSATUR",
        parameters: { algorithm: "dsatur", time_budget_seconds: 30 },
      }),
    );

    expect(optimized.Algorithm.value).toBe("Optimized (annealing)");
    expect(optimized["Optimization time"].value).toBe("30s");
    expect(classic["Optimization time"]).toBeUndefined();
  });

  it("flags back-to-back as unused by Classic", () => {
    const classic = byLabel(
      generationSettings({
        algorithm: "DSATUR",
        parameters: { avoid_back_to_back: true },
      }),
    );
    const optimized = byLabel(
      generationSettings({
        algorithm: "Annealing",
        parameters: { algorithm: "annealing", avoid_back_to_back: false },
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
