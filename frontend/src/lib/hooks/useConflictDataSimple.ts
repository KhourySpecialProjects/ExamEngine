import { useSchedulesStore } from "@/lib/store/schedulesStore";
import type { ConflictMetrics } from "@/lib/types/conflict.types";
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

const DAY_ORDER = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];

/** Conflict types shown as one row per student/instructor. */
export function isPersonConflictType(type: ConflictType): boolean {
  return PERSON_CONFLICT_TYPES.includes(type);
}

/** Person conflict types whose person is an instructor, not a student. */
export function isInstructorConflictType(type: ConflictType): boolean {
  return INSTRUCTOR_CONFLICT_TYPES.includes(type);
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
        },
        instances: new Map(),
      };
      personRows.set(rowKey, group);
      rows.push(group.row);
    }

    const day = conflict.day || "";
    const slots = getSlots(conflict);
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
  const examsByCrn = buildExamsByCrn(currentSchedule?.schedule);

  const rows = buildConflictRows(breakdown, examsByCrn);
  const rowsByType = groupRowsByType(rows);
  const metrics = calculateMetrics(rowsByType);
  const types = Object.keys(rowsByType);

  return { metrics, rowsByType, types };
}
