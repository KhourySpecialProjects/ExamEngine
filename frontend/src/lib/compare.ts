/**
 * Rules of the Compare page that don't depend on React: which schedules the
 * URL names, column moves, differences from the baseline, the settings diff,
 * publishability and the shared chart scales.
 */
import type { ConflictMetric, ScheduleSummary } from "@/lib/api/schedules";
import {
  conflictDescriptions,
  conflictTypeMap,
} from "@/lib/hooks/useConflictData";
import { MAX_COMPARED } from "@/lib/scheduleSelection";
import { type SettingRow, settingRows } from "@/lib/scheduleSettings";

// URL state: /dashboard/compare?ids=a,b,c&base=a

const SCHEDULE_ID =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * Whether `id` can name a schedule. Anything else (e.g. a mangled link) is
 * shown as not available without asking the server, which would reject the
 * whole request.
 */
export function isScheduleId(id: string): boolean {
  return SCHEDULE_ID.test(id);
}

/**
 * The columns the URL names, in order: lowercased (schedule ids are UUIDs),
 * blanks and repeats dropped, at most 4.
 */
export function compareIds(ids: readonly string[] | null): string[] {
  const named = (ids ?? [])
    .map((id) => id.trim().toLowerCase())
    .filter(Boolean);
  return [...new Set(named)].slice(0, MAX_COMPARED);
}

/**
 * The baseline column: `base` when it is an available column, else the first
 * available one (null when none is).
 */
export function baselineId(
  ids: readonly string[],
  base: string | null,
  isAvailable: (id: string) => boolean = () => true,
): string | null {
  const candidates = ids.filter(isAvailable);
  return base && candidates.includes(base) ? base : (candidates[0] ?? null);
}

/** `id` moved one column left (-1) or right (+1); unchanged at an edge. */
export function moveColumn(
  ids: readonly string[],
  id: string,
  offset: -1 | 1,
): string[] {
  const from = ids.indexOf(id);
  const to = from + offset;
  if (from === -1 || to < 0 || to >= ids.length) return [...ids];
  const next = [...ids];
  [next[from], next[to]] = [next[to], next[from]];
  return next;
}

/** `id` added as the last column, unless it is already shown or the page is full. */
export function addColumn(ids: readonly string[], id: string): string[] {
  if (ids.includes(id) || ids.length >= MAX_COMPARED) return [...ids];
  return [...ids, id];
}

// Columns

/** Okabe–Ito colours (colourblind-safe), with the letter colour readable on each. */
export const COLUMN_COLORS = [
  { fill: "#0072B2", text: "#FFFFFF" },
  { fill: "#E69F00", text: "#000000" },
  { fill: "#009E73", text: "#000000" },
  { fill: "#CC79A7", text: "#000000" },
] as const;

export function columnLetter(index: number): string {
  return String.fromCharCode(65 + index);
}

// Differences from the baseline

export type DeltaTone = "better" | "worse" | "same";

export interface Delta {
  /** value − baseline */
  value: number;
  tone: DeltaTone;
}

/** Difference from the baseline; every compared count is better lower. */
export function delta(value: number, baseline: number): Delta {
  const diff = value - baseline;
  if (diff === 0) return { value: 0, tone: "same" };
  return { value: diff, tone: diff < 0 ? "better" : "worse" };
}

/** "+3", "−2" (minus sign) or "±0". */
export function formatDelta(value: number): string {
  if (value === 0) return "±0";
  const size = Math.abs(value).toLocaleString();
  return value > 0 ? `+${size}` : `−${size}`;
}

// Settings

export interface SettingComparison {
  key: SettingRow["key"];
  label: string;
  /** One row per schedule, in column order. */
  rows: SettingRow[];
}

/**
 * Every setting across the schedules, split into those whose shown value
 * differs and those the same in all. A setting one algorithm ignores reads
 * "Not used by …", so it differs from a schedule that used it.
 */
export function compareSettings(summaries: readonly ScheduleSummary[]): {
  differing: SettingComparison[];
  same: SettingComparison[];
} {
  const perSchedule = summaries.map(settingRows);
  const differing: SettingComparison[] = [];
  const same: SettingComparison[] = [];
  (perSchedule[0] ?? []).forEach(({ key, label }, i) => {
    const rows = perSchedule.map((schedule) => schedule[i]);
    const differs = new Set(rows.map((row) => row.value)).size > 1;
    (differs ? differing : same).push({ key, label, rows });
  });
  return { differing, same };
}

// Publishable

const HARD_CONFLICT_METRICS: readonly ConflictMetric[] = [
  "student_double_book",
  "instructor_double_book",
  "student_over_daily_limit",
  "instructor_over_daily_limit",
];

export interface PublishBlocker {
  /** Reads after the count: "3 unscheduled". */
  label: string;
  count: number;
}

/**
 * What stops a schedule from being published as is; empty when nothing does.
 * Hard conflicts add up the people of each hard type (double-booked or over
 * the daily limit), as the Statistics tab lists them.
 */
export function publishBlockers(summary: ScheduleSummary): PublishBlocker[] {
  const hard = HARD_CONFLICT_METRICS.reduce(
    (total, metric) => total + summary.conflicts[metric].people,
    0,
  );
  return [
    { label: "with hard conflicts", count: hard },
    { label: "unscheduled", count: summary.exams.unscheduled },
    { label: "without a room", count: summary.exams.unroomed },
    { label: "over capacity", count: summary.exams.over_capacity },
  ].filter((blocker) => blocker.count > 0);
}

// Conflicts

export interface ConflictRowDefinition {
  metric: ConflictMetric;
  /** The breakdown type: the schedule's Conflicts tab that lists these. */
  type: string;
  label: string;
  definition: string;
  /** What `people` counts: [one, many]. */
  unit: [string, string];
}

const STUDENTS: [string, string] = ["student", "students"];
const INSTRUCTORS: [string, string] = ["instructor", "instructors"];

/** Summary metric → the breakdown type whose label and definition it reuses. */
const CONFLICT_TYPES: Record<ConflictMetric, [string, [string, string]]> = {
  student_double_book: ["student_double_book", STUDENTS],
  student_over_daily_limit: ["student_gt_max_per_day", STUDENTS],
  student_back_to_back: ["back_to_back", STUDENTS],
  instructor_double_book: ["instructor_double_book", INSTRUCTORS],
  instructor_over_daily_limit: ["instructor_gt_max_per_day", INSTRUCTORS],
  instructor_back_to_back: ["back_to_back_instructor", INSTRUCTORS],
  large_courses_late: ["large_course_not_early", ["exam", "exams"]],
};

/** One row per conflict type, in the Conflicts tab's order. */
export const CONFLICT_ROWS: readonly ConflictRowDefinition[] = (
  Object.entries(CONFLICT_TYPES) as [
    ConflictMetric,
    [string, [string, string]],
  ][]
).map(([metric, [type, unit]]) => ({
  metric,
  type,
  label: conflictTypeMap[type],
  definition: conflictDescriptions[type],
  unit,
}));

export function countOf(n: number, [one, many]: [string, string]): string {
  return `${n.toLocaleString()} ${n === 1 ? one : many}`;
}

// Calendar shape: one scale across all columns

const WEEK = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];

/** Minutes after midnight a block label ("11:30AM-1:30PM") starts at. */
function blockStart(label: string): number {
  const match = /^(\d{1,2})(?::(\d{2}))?\s*([AP]M)/i.exec(label.trim());
  if (!match) return Number.POSITIVE_INFINITY;
  const hour =
    (Number(match[1]) % 12) + (match[3].toUpperCase() === "PM" ? 12 : 0);
  return hour * 60 + Number(match[2] ?? 0);
}

function byWeekday(a: string, b: string): number {
  const rank = (day: string) =>
    WEEK.includes(day) ? WEEK.indexOf(day) : WEEK.length;
  return rank(a) - rank(b) || a.localeCompare(b);
}

function byStartTime(a: string, b: string): number {
  return blockStart(a) - blockStart(b) || a.localeCompare(b);
}

export interface ScheduleShape {
  /** Placed exams per day of `CalendarShape.days`. */
  days: number[];
  /** Placed exams per block of `CalendarShape.blocks`. */
  blocks: number[];
  /** Placed exams per [day][block]. */
  matrix: number[][];
}

export interface CalendarShape {
  /** Every day any schedule uses, Monday first. */
  days: string[];
  /** Every block any schedule uses, earliest first. */
  blocks: string[];
  schedules: ScheduleShape[];
  maxDay: number;
  maxBlock: number;
  maxCell: number;
}

/** The schedules' calendars on shared axes, with one maximum per chart type. */
export function calendarShape(
  summaries: readonly ScheduleSummary[],
): CalendarShape {
  const calendars = summaries.map((s) => s.calendar);
  const days = [
    ...new Set(calendars.flatMap((c) => c.days.map((d) => d.day))),
  ].sort(byWeekday);
  const blocks = [
    ...new Set(calendars.flatMap((c) => c.blocks.map((b) => b.label))),
  ].sort(byStartTime);

  const schedules = calendars.map((c) => {
    const dayIndex = c.days.map((d) => d.day);
    const blockIndex = c.blocks.map((b) => b.label);
    const cell = (day: string, block: string) => {
      const d = dayIndex.indexOf(day);
      const b = blockIndex.indexOf(block);
      return d === -1 || b === -1 ? 0 : (c.matrix[d]?.[b] ?? 0);
    };
    return {
      days: days.map((day) => c.days.find((d) => d.day === day)?.exams ?? 0),
      blocks: blocks.map(
        (block) => c.blocks.find((b) => b.label === block)?.exams ?? 0,
      ),
      matrix: days.map((day) => blocks.map((block) => cell(day, block))),
    };
  });

  const max = (values: number[]) => Math.max(0, ...values);
  return {
    days,
    blocks,
    schedules,
    maxDay: max(schedules.flatMap((s) => s.days)),
    maxBlock: max(schedules.flatMap((s) => s.blocks)),
    maxCell: max(schedules.flatMap((s) => s.matrix.flat())),
  };
}
