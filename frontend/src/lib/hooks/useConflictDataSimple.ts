// biome-ignore-all lint/suspicious/noExplicitAny: this file require conflict types definitions
import { useSchedulesStore } from "@/lib/store/schedulesStore";
import type { ScheduleConflicts, ScheduleData } from "../api/schedules";

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

export interface ConflictRow {
  id: string;
  type: ConflictType;
  entity: string;
  day: string;
  block: string;
  course: string;
  crn: string;
  conflictingCourses: string[];
  size: number | null;
  reason: string | null;
}

export type ConflictDataByType = Record<ConflictType, ConflictRow[]>;

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

const MULTI_COURSE_CONFLICT_TYPES: ConflictType[] = [
  "student_double_book",
  "instructor_double_book",
  "student_gt_max_per_day",
  "student_gt3_per_day",
];

// Helper functions
function buildCrnToCourseMap(schedule: ScheduleData): Map<string, string> {
  const map = new Map<string, string>();
  if (!schedule.complete) return map;

  for (const exam of schedule.complete) {
    if (exam.CRN && exam.Course) {
      map.set(String(exam.CRN), exam.Course);
    }
  }
  return map;
}

function getEntity(conflict: any, type: ConflictType): string {
  const isInstructorConflict = INSTRUCTOR_CONFLICT_TYPES.includes(type);

  if (isInstructorConflict) {
    return conflict.instructor_name || conflict.entity_id || "";
  }
  return (
    conflict.student_id || conflict.entity_id || conflict.instructor_id || ""
  );
}

function getConflictingItems(conflict: any): {
  courses: string[];
  crns: string[];
} {
  const courses = [
    ...(conflict.conflicting_course ? [conflict.conflicting_course] : []),
    ...(conflict.conflicting_courses || []),
  ];

  const crns = [
    ...(conflict.conflicting_crn ? [conflict.conflicting_crn] : []),
    ...(conflict.conflicting_crns || []),
  ].map(String);

  return { courses, crns };
}

function createMultiCourseRows(
  conflict: any,
  idx: number,
  type: ConflictType,
  entity: string,
  crnToCourseMap: Map<string, string>,
): ConflictRow[] {
  const { courses: conflictingCourses, crns: conflictingCrns } =
    getConflictingItems(conflict);
  const day = conflict.day || "";
  const block = conflict.block?.toString() || conflict.block_time || "";

  // Collect all courses involved
  const allCourses: Array<{ course: string; crn: string }> = [];

  // Add main course
  if (conflict.course || conflict.crn) {
    allCourses.push({
      course: conflict.course || "",
      crn: conflict.crn?.toString() || "",
    });
  }

  // Add conflicting courses
  if (conflictingCourses.length > 0) {
    conflictingCourses.forEach((course, i) => {
      allCourses.push({
        course,
        crn: conflictingCrns[i] || "",
      });
    });
  } else if (conflictingCrns.length > 0) {
    conflictingCrns.forEach((crn) => {
      allCourses.push({
        course: crnToCourseMap.get(crn) || "",
        crn,
      });
    });
  }

  // Create a row for each course
  return allCourses.map((courseInfo, courseIdx) => {
    const otherCourses = allCourses
      .filter((_, i) => i !== courseIdx)
      .map((c) => c.course || c.crn)
      .filter(Boolean);

    return {
      id: `conflict-${idx}-course-${courseIdx}`,
      type,
      entity,
      day,
      block,
      course: courseInfo.course,
      crn: courseInfo.crn,
      conflictingCourses: otherCourses,
      size: conflict.size || null,
      reason: conflict.reason || null,
    };
  });
}

function createSingleRow(
  conflict: any,
  idx: number,
  type: ConflictType,
  entity: string,
): ConflictRow {
  const { courses: conflictingCourses, crns: conflictingCrns } =
    getConflictingItems(conflict);

  return {
    id: `conflict-${idx}`,
    type,
    entity,
    day: conflict.day || "",
    block: conflict.block?.toString() || conflict.block_time || "",
    course: conflict.course || "",
    crn: conflict.crn?.toString() || "",
    conflictingCourses:
      conflictingCourses.length > 0 ? conflictingCourses : conflictingCrns,
    size: conflict.size || null,
    reason: conflict.reason || null,
  };
}

function convertBreakdownToRows(
  breakdown: any[],
  crnToCourseMap: Map<string, string>,
): ConflictRow[] {
  const rows: ConflictRow[] = [];

  breakdown.forEach((conflict, idx) => {
    const type: ConflictType = conflict.conflict_type || "unknown";
    const entity = getEntity(conflict, type);
    const { courses, crns } = getConflictingItems(conflict);
    const hasConflictingItems = courses.length > 0 || crns.length > 0;

    if (MULTI_COURSE_CONFLICT_TYPES.includes(type) && hasConflictingItems) {
      rows.push(
        ...createMultiCourseRows(conflict, idx, type, entity, crnToCourseMap),
      );
    } else {
      rows.push(createSingleRow(conflict, idx, type, entity));
    }
  });

  return rows;
}

function calculateMetrics(breakdown: any[]): ConflictMetrics {
  const countByType = (types: ConflictType[]) =>
    breakdown.filter((c) => types.includes(c.conflict_type)).length;

  return {
    hard_student_conflicts: countByType(["student_double_book"]),
    hard_instructor_conflicts: countByType(["instructor_double_book"]),
    student_gt3_per_day: countByType(["student_gt_max_per_day"]),
    students_back_to_back: countByType([
      "back_to_back",
      "back_to_back_student",
    ]),
    instructors_back_to_back: countByType(["back_to_back_instructor"]),
    large_courses_not_early: countByType(["large_course_not_early"]),
  };
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
  const conflicts = currentSchedule?.conflicts ?? ({} as ScheduleConflicts);
  const schedule = currentSchedule?.schedule;

  const breakdown: any[] = conflicts.breakdown ?? [];
  const crnToCourseMap = buildCrnToCourseMap(schedule as ScheduleData);

  const rows = convertBreakdownToRows(breakdown, crnToCourseMap);
  const metrics = calculateMetrics(breakdown);
  const rowsByType = groupRowsByType(rows);
  const types = Object.keys(rowsByType);

  return { metrics, rowsByType, types };
}
