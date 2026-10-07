import type {
  LateAddition,
  ScheduleResult,
  ScheduleSettings,
  ScheduleSummary,
} from "@/lib/api/schedules";

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

/** A generated schedule's detail response with no exams; override what a test needs. */
export function makeSchedule(
  overrides: Partial<ScheduleResult> = {},
): ScheduleResult {
  return {
    schedule_id: "s1",
    dataset_id: "d1",
    dataset_name: "Spring data",
    schedule_name: "Fall",
    created_at: "2026-01-02T10:00:00",
    algorithm: "DSATUR",
    status: "Completed",
    summary: makeSummary(),
    conflicts: { total: 0, breakdown: [], details: {} },
    failures: [],
    schedule: { complete: [], calendar: {}, total_exams: 0 },
    parameters: {},
    is_owner: true,
    is_shared: false,
    created_by_user_id: "u1",
    created_by_user_name: "Ada",
    lineage: {
      based_on: null,
      original: null,
      late_additions: [],
      newer_versions: [],
    },
    ...overrides,
  };
}

/** One stored late addition: clear, Monday first block. */
export function makeLateAddition(
  overrides: Partial<LateAddition> = {},
): LateAddition {
  return {
    crn: "90001",
    course_code: "CS 1000",
    instructor_id: "I-1",
    size: 30,
    day: 0,
    day_name: "Monday",
    block: 0,
    block_time: "8AM-10AM",
    room: "Hall A",
    outcome: "clear",
    conflicts: {
      student_double_book: 0,
      student_over_daily_limit: 0,
      instructor_double_book: 0,
      instructor_over_daily_limit: 0,
      back_to_back_students: 0,
      back_to_back_instructor: 0,
      large_course_late: 0,
    },
    added_by: "u1",
    added_by_name: "Ada",
    added_at: "2026-01-03T09:30:00",
    schedule_id: "s2",
    ...overrides,
  };
}
