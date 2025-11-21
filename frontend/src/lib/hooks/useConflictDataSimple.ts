import { useScheduleStore } from "@/lib/store/scheduleStore";

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
  const metrics = conflicts.metrics ?? {};
  const rows: ConflictRow[] = conflicts.rows ?? [];

  const rowsByType: ConflictDataByType = {};
  for (const r of rows) {
    if (!rowsByType[r.type]) rowsByType[r.type] = [];
    rowsByType[r.type].push(r);
  }

  const types = Object.keys(rowsByType);
  return { metrics, rowsByType, types };
}
