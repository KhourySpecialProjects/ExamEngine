import type { ScheduleSettings, ScheduleSummary } from "@/lib/api/schedules";

/** One generation setting as the UI shows it. */
export interface SettingRow {
  key: keyof ScheduleSettings;
  label: string;
  value: string;
  note?: string;
  /** The run's algorithm ignores this setting; `value` says so. */
  unused: boolean;
}

interface SettingDefinition {
  key: keyof ScheduleSettings;
  label: string;
  format: (settings: ScheduleSettings) => string;
  /** Shown when an older run didn't record the setting (see `settings_assumed`). */
  assumedNote?: string;
}

export const ENGINE_NAMES: Record<ScheduleSettings["algorithm"], string> = {
  dsatur: "Classic",
  annealing: "Optimized",
};

const NOT_RECORDED = "Not recorded";

function yesNo(value: boolean | null): string {
  if (value === null) return NOT_RECORDED;
  return value ? "Yes" : "No";
}

function count(value: number | null): string {
  return value === null ? NOT_RECORDED : String(value);
}

/**
 * Every generation setting, in display order. The schedule header and the
 * Compare page both list these, so a new setting only needs an entry here.
 */
export const SETTING_DEFINITIONS: readonly SettingDefinition[] = [
  {
    key: "algorithm",
    label: "Algorithm",
    format: (s) =>
      s.algorithm === "annealing"
        ? "Optimized (annealing)"
        : "Classic (DSATUR)",
  },
  {
    key: "time_budget_seconds",
    label: "Optimization time",
    format: (s) =>
      s.time_budget_seconds === null
        ? NOT_RECORDED
        : `${s.time_budget_seconds}s`,
  },
  { key: "max_days", label: "Max exam days", format: (s) => count(s.max_days) },
  {
    key: "blocks_per_day",
    label: "Exam blocks per day",
    format: (s) => String(s.blocks_per_day),
    assumedNote: "Not recorded; the only option at the time",
  },
  {
    key: "student_max_per_day",
    label: "Max exams per student per day",
    format: (s) => count(s.student_max_per_day),
  },
  {
    key: "instructor_max_per_day",
    label: "Max exams per instructor per day",
    format: (s) => count(s.instructor_max_per_day),
  },
  {
    key: "avoid_back_to_back",
    label: "Avoid back-to-back",
    format: (s) => yesNo(s.avoid_back_to_back),
  },
  {
    key: "prioritize_large_courses",
    label: "Prioritize large classes",
    format: (s) => yesNo(s.prioritize_large_courses),
  },
];

/**
 * The settings a schedule was generated with, as the server resolved them
 * from its run. A setting the algorithm ignores reads "Not used by …"
 * instead of its stored value.
 */
export function settingRows({
  settings,
  settings_assumed: assumed,
  settings_unused: unused,
}: Pick<
  ScheduleSummary,
  "settings" | "settings_assumed" | "settings_unused"
>): SettingRow[] {
  return SETTING_DEFINITIONS.map(({ key, label, format, assumedNote }) =>
    unused.includes(key)
      ? {
          key,
          label,
          value: `Not used by ${ENGINE_NAMES[settings.algorithm]}`,
          unused: true,
        }
      : {
          key,
          label,
          value: format(settings),
          note: assumed.includes(key) ? assumedNote : undefined,
          unused: false,
        },
  );
}
