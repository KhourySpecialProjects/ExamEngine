import { useSchedulesStore as useScheduleStore } from "@/lib/store/schedulesStore";

export type ConflictType =
  | "student_double_book"
  | "instructor_double_book"
  | "student_gt3_per_day"
  | "back_to_back_student"
  | "back_to_back_instructor"
  | "large_course_not_early"
  | string;

export type ConflictRow = {
  id: string;
  type: ConflictType;
  entity: string;
  day: string;
  block: string;
  course: string;
  crn: string;
  conflictingCourses: string[];
  size?: number | null;
  reason?: string | null;
  [key: string]: any;
};

export type ConflictDataByType = Record<string, ConflictRow[]>;

export function useConflictDataSimple() {
  const currentSchedule = useScheduleStore((s) => s.currentSchedule);
  const conflicts = currentSchedule?.conflicts ?? {};
  
  // Backend returns breakdown array, not rows
  const breakdown: any[] = conflicts.breakdown ?? [];
  
  // Convert breakdown to ConflictRow format
  const rows: ConflictRow[] = breakdown.map((c, idx) => ({
    id: `conflict-${idx}`,
    type: c.conflict_type || "unknown",
    entity: c.student_id || c.entity_id || c.instructor_id || "",
    day: c.day || "",
    block: c.block?.toString() || c.block_time || "",
    course: c.course || "",
    crn: c.crn?.toString() || "",
    conflictingCourses: c.conflicting_courses || c.conflicting_crns?.map((cc: any) => String(cc)) || [],
    size: c.size || null,
    reason: c.reason || null,
    ...c, // Include all other fields
  }));

  // Calculate metrics from breakdown
  const metrics = {
    hard_student_conflicts: breakdown.filter((c) => c.conflict_type === "student_double_book").length,
    hard_instructor_conflicts: breakdown.filter((c) => c.conflict_type === "instructor_double_book").length,
    student_gt3_per_day: breakdown.filter((c) => c.conflict_type === "student_gt_max_per_day").length,
    students_back_to_back: breakdown.filter((c) => c.conflict_type === "back_to_back" || c.conflict_type === "back_to_back_student").length,
    instructors_back_to_back: breakdown.filter((c) => c.conflict_type === "back_to_back_instructor").length,
    large_courses_not_early: breakdown.filter((c) => c.conflict_type === "large_course_not_early").length,
  };

  const rowsByType: ConflictDataByType = {};
  for (const r of rows) {
    if (!rowsByType[r.type]) rowsByType[r.type] = [];
    rowsByType[r.type].push(r);
  }

  const types = Object.keys(rowsByType);
  return { metrics, rowsByType, types };
}
