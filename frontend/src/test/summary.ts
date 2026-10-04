import type { ScheduleSettings, ScheduleSummary } from "@/lib/api/schedules";

/** A Classic run's settings as the server reports them. */
export const CLASSIC_SETTINGS: ScheduleSettings = {
  algorithm: "dsatur",
  blocks_per_day: 5,
  time_budget_seconds: 15,
  max_days: 7,
  student_max_per_day: 2,
  instructor_max_per_day: 2,
  avoid_back_to_back: true,
  prioritize_large_courses: false,
};

const noConflicts = { people: 0, instances: 0 };

/** A publishable Classic schedule's summary: 3 exams, no conflicts. */
export function makeSummary(
  overrides: Partial<ScheduleSummary> = {},
): ScheduleSummary {
  return {
    settings: CLASSIC_SETTINGS,
    settings_assumed: [],
    settings_unused: ["time_budget_seconds", "avoid_back_to_back"],
    unique_students: 10,
    exams: {
      total: 3,
      placed: 3,
      unscheduled: 0,
      unroomed: 0,
      over_capacity: 0,
    },
    unscheduled: { exams: [], students: 0, groups: [], other_crns: [] },
    unroomed: { exams: [], students: 0 },
    over_capacity: [],
    conflicts: {
      student_double_book: noConflicts,
      instructor_double_book: noConflicts,
      student_over_daily_limit: noConflicts,
      instructor_over_daily_limit: noConflicts,
      student_back_to_back: noConflicts,
      instructor_back_to_back: noConflicts,
      large_courses_late: noConflicts,
    },
    rooms: {
      used: 1,
      average_fill: 50,
      fill_buckets: {
        under_50: 0,
        from_50_to_75: 3,
        from_75_to_90: 0,
        from_90_to_100: 0,
      },
    },
    calendar: { slots_used: 0, days_used: 0, days: [], blocks: [], matrix: [] },
    groups: {
      combined: { groups: 0, sections: 0, students: 0 },
      common: { groups: 0, sections: 0, students: 0 },
    },
    blockouts: { rooms: 0, slots: 0 },
    ...overrides,
  };
}
