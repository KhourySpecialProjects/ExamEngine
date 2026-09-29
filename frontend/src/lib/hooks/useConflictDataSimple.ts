import { useSchedulesStore } from "@/lib/store/schedulesStore";
import type { ConflictBreakdown, ScheduleData } from "../api/schedules";

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
}

/** One conflict occurrence for a person: a day + time slot and the exams involved. */
export interface ConflictInstance {
  day: string;
  time: string;
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

/** Person-based metrics count distinct people; large_courses_not_early counts courses. */
export interface ConflictMetrics {
  hard_student_conflicts: number;
  hard_instructor_conflicts: number;
  student_gt3_per_day: number;
  students_back_to_back: number;
  instructors_back_to_back: number;
  large_courses_not_early: number;
}

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

const DAY_ORDER = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];

/** Conflict types shown as one row per student/instructor. */
export function isPersonConflictType(type: ConflictType): boolean {
  return PERSON_CONFLICT_TYPES.includes(type);
}

// Helper functions
function buildCrnToCourseMap(
  schedule: ScheduleData | undefined,
): Map<string, string> {
  const map = new Map<string, string>();
  if (!schedule?.complete) return map;

  for (const exam of schedule.complete) {
    if (exam.CRN && exam.Course) {
      map.set(String(exam.CRN), exam.Course);
    }
  }
  return map;
}

function getEntity(conflict: ConflictBreakdown, type: ConflictType): string {
  const entity = INSTRUCTOR_CONFLICT_TYPES.includes(type)
    ? conflict.instructor_name || conflict.entity_id
    : conflict.student_id || conflict.entity_id;
  // IDs are strings (leading zeros matter); never coerce to number.
  return entity == null ? "" : String(entity);
}

function getTimeLabel(conflict: ConflictBreakdown): string {
  if (conflict.block_time) return conflict.block_time;
  const blockTimes = (conflict.block_times ?? []).filter(Boolean);
  if (blockTimes.length > 0) return blockTimes.join(", ");
  const blocks = conflict.blocks?.length
    ? conflict.blocks
    : [conflict.block].filter((b) => b != null);
  return blocks.length > 0 ? `Block ${blocks.join(", ")}` : "";
}

/** [day index Mon..Sun, first block index]; unknown values sort last. */
function getSortKey(conflict: ConflictBreakdown): [number, number] {
  const dayIdx = DAY_ORDER.indexOf(
    String(conflict.day ?? "")
      .slice(0, 3)
      .toLowerCase(),
  );
  const firstBlock = conflict.blocks?.length
    ? conflict.blocks[0]
    : conflict.block;
  const blockIdx = firstBlock == null ? Number.NaN : Number(firstBlock);
  return [
    dayIdx === -1 ? DAY_ORDER.length : dayIdx,
    Number.isNaN(blockIdx) ? Number.POSITIVE_INFINITY : blockIdx,
  ];
}

/** The record's own course plus its conflicting courses. */
function getCourses(
  conflict: ConflictBreakdown,
  crnToCourseMap: Map<string, string>,
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
    // The backend reports "Unknown" when it could not resolve a course code.
    const course =
      (name && name !== "Unknown" ? name : crnToCourseMap.get(crn)) || "";
    if (crn || course) courses.push({ course, crn });
  }
  return courses;
}

function mergeCourses(target: ConflictCourse[], incoming: ConflictCourse[]) {
  for (const c of incoming) {
    const existing = target.find((t) =>
      c.crn ? t.crn === c.crn : !t.crn && t.course === c.course,
    );
    if (!existing) target.push({ ...c });
    else if (!existing.course) existing.course = c.course;
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
  crnToCourseMap: Map<string, string>,
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
        },
        instances: new Map(),
      };
      personRows.set(rowKey, group);
      rows.push(group.row);
    }

    const day = conflict.day || "";
    const time = getTimeLabel(conflict);
    const instanceKey = `${day}\u0000${time}`;
    let entry = group.instances.get(instanceKey);
    if (!entry) {
      entry = {
        instance: { day, time, courses: [] },
        sortKey: getSortKey(conflict),
      };
      group.instances.set(instanceKey, entry);
    }
    mergeCourses(entry.instance.courses, getCourses(conflict, crnToCourseMap));
  });

  for (const { row, instances } of personRows.values()) {
    row.instances = [...instances.values()]
      .sort(
        (a, b) => a.sortKey[0] - b.sortKey[0] || a.sortKey[1] - b.sortKey[1],
      )
      .map(({ instance }) => ({
        ...instance,
        courses: instance.courses.sort(
          (a, b) =>
            a.course.localeCompare(b.course) || a.crn.localeCompare(b.crn),
        ),
      }));
    row.conflictCount = row.instances.length;
  }

  return rows;
}

function groupRowsByType(rows: ConflictRow[]): ConflictDataByType {
  return rows.reduce((acc, row) => {
    if (!acc[row.type]) acc[row.type] = [];
    acc[row.type].push(row);
    return acc;
  }, {} as ConflictDataByType);
}

/** Metrics match the tabs: distinct people per person type, courses otherwise. */
function calculateMetrics(rowsByType: ConflictDataByType): ConflictMetrics {
  const countRows = (types: ConflictType[]) =>
    new Set(
      types.flatMap((t) => (rowsByType[t] ?? []).map((r) => r.entity || r.id)),
    ).size;

  return {
    hard_student_conflicts: countRows(["student_double_book"]),
    hard_instructor_conflicts: countRows(["instructor_double_book"]),
    student_gt3_per_day: countRows([
      "student_gt_max_per_day",
      "student_gt3_per_day",
    ]),
    students_back_to_back: countRows(["back_to_back", "back_to_back_student"]),
    instructors_back_to_back: countRows(["back_to_back_instructor"]),
    large_courses_not_early: countRows(["large_course_not_early"]),
  };
}

export function useConflictDataSimple() {
  const currentSchedule = useSchedulesStore((s) => s.currentSchedule);
  const breakdown = currentSchedule?.conflicts?.breakdown ?? [];
  const crnToCourseMap = buildCrnToCourseMap(currentSchedule?.schedule);

  const rows = buildConflictRows(breakdown, crnToCourseMap);
  const rowsByType = groupRowsByType(rows);
  const metrics = calculateMetrics(rowsByType);
  const types = Object.keys(rowsByType);

  return { metrics, rowsByType, types };
}
