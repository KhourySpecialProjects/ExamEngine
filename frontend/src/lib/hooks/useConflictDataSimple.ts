import { useSchedulesStore } from "@/lib/store/schedulesStore";
import type {
  ConflictBreakdown,
  ScheduleData,
  ScheduleExam,
} from "../api/schedules";

// Types
export type ConflictType =
  | "student_double_book"
  | "instructor_double_book"
  | "student_gt3_per_day"
  | "student_gt_max_per_day"
  | "back_to_back"
  | "back_to_back_student"
  | "back_to_back_instructor"
  | "large_course_not_early"
  | string;

export interface ConflictCourse {
  course: string;
  crn: string;
  /** The scheduled exam for this CRN (room, size, instructor), when known. */
  exam?: ScheduleExam;
}

/** One conflict occurrence for a person: a day + time slot and the exams involved. */
export interface ConflictInstance {
  day: string;
  /** Display/grouping label: `slots` joined. */
  time: string;
  /** Individual time slots, e.g. each block of a back-to-back run. */
  slots: string[];
  courses: ConflictCourse[];
}

/** One row per (conflict type, student/instructor), listing all their conflicts. */
export interface PersonConflictRow {
  kind: "person";
  id: string;
  type: ConflictType;
  entity: string;
  /** Chronological (day, then block). */
  instances: ConflictInstance[];
  conflictCount: number;
  /** [day index Mon..Sun, block] of the earliest instance; sorts Day/Time. */
  earliest: [number, number];
}

/** One row per backend record, for conflicts not tied to a person (e.g. large courses). */
export interface RecordConflictRow {
  kind: "record";
  id: string;
  type: ConflictType;
  entity: string;
  day: string;
  block: string;
  course: string;
  crn: string;
  size: number | null;
}

export type ConflictRow = PersonConflictRow | RecordConflictRow;

export type ConflictDataByType = Record<ConflictType, ConflictRow[]>;

// Constants
const INSTRUCTOR_CONFLICT_TYPES: ConflictType[] = [
  "back_to_back_instructor",
  "instructor_double_book",
  "instructor_gt_max_per_day",
];

const PERSON_CONFLICT_TYPES: ConflictType[] = [
  "student_double_book",
  "student_gt_max_per_day",
  "student_gt3_per_day",
  "back_to_back",
  "back_to_back_student",
  ...INSTRUCTOR_CONFLICT_TYPES,
];

/**
 * Per-day limit types. Their records carry only the exam that went over the
 * limit, not the person's other exams that day (EXENG-46), so they are shown
 * as the days a person is over the limit, without times or exams.
 */
const PER_DAY_LIMIT_CONFLICT_TYPES: ConflictType[] = [
  "student_gt_max_per_day",
  "student_gt3_per_day",
  "instructor_gt_max_per_day",
];

const DAY_ORDER = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];

/** Conflict types shown as one row per student/instructor. */
export function isPersonConflictType(type: ConflictType): boolean {
  return PERSON_CONFLICT_TYPES.includes(type);
}

/** Person conflict types whose person is an instructor, not a student. */
export function isInstructorConflictType(type: ConflictType): boolean {
  return INSTRUCTOR_CONFLICT_TYPES.includes(type);
}

/** Per-day limit types: one sub-row per day the person is over the limit. */
export function isPerDayLimitConflictType(type: ConflictType): boolean {
  return PER_DAY_LIMIT_CONFLICT_TYPES.includes(type);
}

/**
 * Back-to-back records carry time slots but no courses (EXENG-42), so they
 * cannot be counted per course.
 */
const BACK_TO_BACK_CONFLICT_TYPES: ConflictType[] = [
  "back_to_back",
  "back_to_back_student",
  "back_to_back_instructor",
];

export function isBackToBackConflictType(type: ConflictType): boolean {
  return BACK_TO_BACK_CONFLICT_TYPES.includes(type);
}

// Helper functions
function buildExamsByCrn(
  schedule: ScheduleData | undefined,
): Map<string, ScheduleExam> {
  const map = new Map<string, ScheduleExam>();
  for (const exam of schedule?.complete ?? []) {
    if (exam.CRN) map.set(String(exam.CRN), exam);
  }
  return map;
}

function getEntity(conflict: ConflictBreakdown, type: ConflictType): string {
  const entity = isInstructorConflictType(type)
    ? conflict.instructor_name || conflict.entity_id
    : conflict.student_id || conflict.entity_id;
  // IDs are strings (leading zeros matter); never coerce to number.
  return entity == null ? "" : String(entity);
}

function getSlots(conflict: ConflictBreakdown): string[] {
  if (conflict.block_time) return [conflict.block_time];
  const blockTimes = (conflict.block_times ?? []).filter(Boolean);
  if (blockTimes.length > 0) return blockTimes;
  const blocks = conflict.blocks?.length
    ? conflict.blocks
    : [conflict.block].filter((b) => b != null);
  return blocks.map((b) => `Block ${b}`);
}

/** [day index Mon..Sun, block index]; unknown values sort last. */
function dayBlockKey(
  day: string | null | undefined,
  block: number | string | null | undefined,
): [number, number] {
  const dayIdx = DAY_ORDER.indexOf(
    String(day ?? "")
      .slice(0, 3)
      .toLowerCase(),
  );
  const blockIdx = block == null ? Number.NaN : Number(block);
  return [
    dayIdx === -1 ? DAY_ORDER.length : dayIdx,
    Number.isNaN(blockIdx) ? Number.POSITIVE_INFINITY : blockIdx,
  ];
}

function getSortKey(conflict: ConflictBreakdown): [number, number] {
  const firstBlock = conflict.blocks?.length
    ? conflict.blocks[0]
    : conflict.block;
  return dayBlockKey(conflict.day, firstBlock);
}

/** The record's own course plus its conflicting courses. */
function getCourses(
  conflict: ConflictBreakdown,
  examsByCrn: Map<string, ScheduleExam>,
): ConflictCourse[] {
  const conflictingCrns = conflict.conflicting_crns ?? [];
  const conflictingCourses = conflict.conflicting_courses ?? [];
  const pairs: Array<[unknown, string | null | undefined]> = [
    [conflict.crn, conflict.course],
    [conflict.conflicting_crn, conflict.conflicting_course],
  ];
  // The backend emits conflicting_crns/conflicting_courses as parallel lists.
  const n = Math.max(conflictingCrns.length, conflictingCourses.length);
  for (let i = 0; i < n; i++) {
    pairs.push([conflictingCrns[i], conflictingCourses[i]]);
  }

  const courses: ConflictCourse[] = [];
  for (const [rawCrn, name] of pairs) {
    const crn = rawCrn == null ? "" : String(rawCrn);
    const exam = crn ? examsByCrn.get(crn) : undefined;
    // The backend reports "Unknown" when it could not resolve a course code.
    const course = (name && name !== "Unknown" ? name : exam?.Course) || "";
    if (!crn && !course) continue;
    courses.push(exam ? { course, crn, exam } : { course, crn });
  }
  return courses;
}

function mergeCourses(target: ConflictCourse[], incoming: ConflictCourse[]) {
  for (const c of incoming) {
    const existing = target.find((t) =>
      c.crn ? t.crn === c.crn : !t.crn && t.course === c.course,
    );
    if (!existing) {
      target.push({ ...c });
      continue;
    }
    if (!existing.course) existing.course = c.course;
    if (!existing.exam && c.exam) existing.exam = c.exam;
  }
}

/**
 * Convert the flat backend breakdown into table rows. Person-based conflicts
 * collapse to one row per (type, person) whose instances are merged by
 * (day, time), so an N-way double-book is a single instance with N courses.
 * Other types (e.g. large_course_not_early) stay one row per record.
 */
export function buildConflictRows(
  breakdown: ConflictBreakdown[],
  examsByCrn: Map<string, ScheduleExam>,
): ConflictRow[] {
  const rows: ConflictRow[] = [];
  const personRows = new Map<
    string,
    {
      row: PersonConflictRow;
      instances: Map<
        string,
        { instance: ConflictInstance; sortKey: [number, number] }
      >;
    }
  >();

  breakdown.forEach((conflict, idx) => {
    const type: ConflictType = conflict.conflict_type || "unknown";
    const entity = getEntity(conflict, type);

    if (!isPersonConflictType(type)) {
      rows.push({
        kind: "record",
        id: `conflict-${idx}`,
        type,
        entity,
        day: conflict.day || "",
        block: conflict.block?.toString() || conflict.block_time || "",
        course: conflict.course || "",
        crn: conflict.crn?.toString() || "",
        size: conflict.size || null,
      });
      return;
    }

    // Records without a person are unrelated; never merge them under "".
    const rowKey = entity ? `${type}\u0000${entity}` : `record-${idx}`;
    let group = personRows.get(rowKey);
    if (!group) {
      group = {
        row: {
          kind: "person",
          id: entity ? `${type}:${entity}` : `conflict-${idx}`,
          type,
          entity,
          instances: [],
          conflictCount: 0,
          earliest: [DAY_ORDER.length, Number.POSITIVE_INFINITY],
        },
        instances: new Map(),
      };
      personRows.set(rowKey, group);
      rows.push(group.row);
    }

    const day = conflict.day || "";
    // Per-day limit conflicts are about the whole day: merge by day alone.
    const slots = isPerDayLimitConflictType(type) ? [] : getSlots(conflict);
    const time = slots.join(", ");
    const instanceKey = `${day}\u0000${time}`;
    let entry = group.instances.get(instanceKey);
    if (!entry) {
      entry = {
        instance: { day, time, slots, courses: [] },
        sortKey: getSortKey(conflict),
      };
      group.instances.set(instanceKey, entry);
    }
    mergeCourses(entry.instance.courses, getCourses(conflict, examsByCrn));
  });

  for (const { row, instances } of personRows.values()) {
    const sorted = [...instances.values()].sort((a, b) =>
      compareKeys(a.sortKey, b.sortKey),
    );
    row.instances = sorted.map(({ instance }) => ({
      ...instance,
      courses: instance.courses.sort(
        (a, b) =>
          a.course.localeCompare(b.course) || a.crn.localeCompare(b.crn),
      ),
    }));
    row.conflictCount = row.instances.length;
    row.earliest = sorted[0].sortKey;
  }

  return rows;
}

// Sorting

export type SortDirection = "asc" | "desc";

export interface SortState<C extends string> {
  column: C;
  direction: SortDirection;
}

/** Person-tab sort columns; Day and Time both sort by the earliest conflict. */
export type PersonSortColumn = "entity" | "conflictCount" | "earliest";

export type RecordSortColumn = keyof Pick<
  RecordConflictRow,
  "entity" | "day" | "block" | "course" | "crn" | "size"
>;

export type CourseSortColumn = "course" | "crn" | "people" | "conflictCount";

function compareKeys(a: [number, number], b: [number, number]): number {
  return a[0] - b[0] || a[1] - b[1];
}

/** IDs stay strings: "000000010" sorts before "9" (no numeric coercion). */
function compareText(a: string, b: string): number {
  // Empty values last in ascending order.
  if (!a || !b) return (a ? 0 : 1) - (b ? 0 : 1);
  return a.localeCompare(b);
}

function compareNumbers(a: number | null, b: number | null): number {
  return (a ?? Number.NEGATIVE_INFINITY) - (b ?? Number.NEGATIVE_INFINITY);
}

/** Stable sort; ties keep their input order in both directions. */
function sortWith<T>(
  items: T[],
  compare: (a: T, b: T) => number,
  direction: SortDirection,
): T[] {
  const sign = direction === "asc" ? 1 : -1;
  return [...items].sort((a, b) => sign * compare(a, b) || 0);
}

/** Sorts whole people; each person's instances stay together and chronological. */
export function sortPersonRows(
  rows: PersonConflictRow[],
  { column, direction }: SortState<PersonSortColumn>,
): PersonConflictRow[] {
  const compare: Record<
    PersonSortColumn,
    (a: PersonConflictRow, b: PersonConflictRow) => number
  > = {
    entity: (a, b) => compareText(a.entity, b.entity),
    conflictCount: (a, b) => a.conflictCount - b.conflictCount,
    earliest: (a, b) => compareKeys(a.earliest, b.earliest),
  };
  return sortWith(rows, compare[column], direction);
}

export function sortRecordRows(
  rows: RecordConflictRow[],
  { column, direction }: SortState<RecordSortColumn>,
): RecordConflictRow[] {
  const blockOf = (r: RecordConflictRow) => {
    const n = Number(r.block);
    return r.block === "" || Number.isNaN(n) ? null : n;
  };
  const compare: Record<
    RecordSortColumn,
    (a: RecordConflictRow, b: RecordConflictRow) => number
  > = {
    entity: (a, b) => compareText(a.entity, b.entity),
    day: (a, b) =>
      compareKeys(
        dayBlockKey(a.day, blockOf(a)),
        dayBlockKey(b.day, blockOf(b)),
      ),
    block: (a, b) => compareNumbers(blockOf(a), blockOf(b)),
    course: (a, b) => compareText(a.course, b.course),
    crn: (a, b) => compareText(a.crn, b.crn),
    size: (a, b) => compareNumbers(a.size, b.size),
  };
  return sortWith(rows, compare[column], direction);
}

// Per-course view

/** One course (CRN) and the people whose conflicts of one type involve it. */
export interface CourseConflictSummary {
  course: string;
  crn: string;
  exam?: ScheduleExam;
  /** Distinct students/instructors, in first-seen order. */
  people: string[];
  /** Conflict instances (across all those people) that include this course. */
  conflictCount: number;
}

/**
 * Per-course summary of one conflict type's rows: a course counts for a person
 * when it is one of the courses in one of that person's conflict instances.
 * Sorted by distinct people, descending, then course. Record rows and
 * instances without courses (back-to-back, EXENG-42) contribute nothing.
 */
export function summarizeConflictsByCourse(
  rows: ConflictRow[],
): CourseConflictSummary[] {
  const byCourse = new Map<
    string,
    { summary: CourseConflictSummary; personKeys: Set<string> }
  >();
  for (const row of rows) {
    if (row.kind !== "person") continue;
    for (const instance of row.instances) {
      for (const c of instance.courses) {
        const key = c.crn ? `crn:${c.crn}` : `course:${c.course}`;
        let entry = byCourse.get(key);
        if (!entry) {
          entry = {
            summary: {
              course: c.course,
              crn: c.crn,
              ...(c.exam && { exam: c.exam }),
              people: [],
              conflictCount: 0,
            },
            personKeys: new Set(),
          };
          byCourse.set(key, entry);
        }
        entry.summary.conflictCount += 1;
        // Rows without a person are distinct records, never one person "".
        const personKey = row.entity || row.id;
        if (!entry.personKeys.has(personKey)) {
          entry.personKeys.add(personKey);
          entry.summary.people.push(row.entity);
        }
      }
    }
  }
  return sortCourseSummaries(
    sortWith(
      [...byCourse.values()].map((e) => e.summary),
      (a, b) => compareText(a.course, b.course) || compareText(a.crn, b.crn),
      "asc",
    ),
    { column: "people", direction: "desc" },
  );
}

export function sortCourseSummaries(
  rows: CourseConflictSummary[],
  { column, direction }: SortState<CourseSortColumn>,
): CourseConflictSummary[] {
  const compare: Record<
    CourseSortColumn,
    (a: CourseConflictSummary, b: CourseConflictSummary) => number
  > = {
    course: (a, b) => compareText(a.course, b.course),
    crn: (a, b) => compareText(a.crn, b.crn),
    people: (a, b) => a.people.length - b.people.length,
    conflictCount: (a, b) => a.conflictCount - b.conflictCount,
  };
  return sortWith(rows, compare[column], direction);
}

function groupRowsByType(rows: ConflictRow[]): ConflictDataByType {
  return rows.reduce((acc, row) => {
    if (!acc[row.type]) acc[row.type] = [];
    acc[row.type].push(row);
    return acc;
  }, {} as ConflictDataByType);
}

export function useConflictDataSimple() {
  const currentSchedule = useSchedulesStore((s) => s.currentSchedule);
  const breakdown = currentSchedule?.conflicts?.breakdown ?? [];
  const examsByCrn = buildExamsByCrn(currentSchedule?.schedule);

  const rows = buildConflictRows(breakdown, examsByCrn);
  const rowsByType = groupRowsByType(rows);
  const types = Object.keys(rowsByType);

  return { rowsByType, types };
}
