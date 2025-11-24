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
  const schedule = currentSchedule?.schedule;
  
  // Backend returns breakdown array, not rows
  const breakdown: any[] = conflicts.breakdown ?? [];
  
  // Build a map of CRN to course name from the schedule for lookup
  const crnToCourseMap = new Map<string, string>();
  if (schedule?.complete) {
    schedule.complete.forEach((exam: any) => {
      if (exam.CRN && exam.Course) {
        crnToCourseMap.set(String(exam.CRN), exam.Course);
      }
    });
  }
  
  // Convert breakdown to ConflictRow format
  // For conflicts involving multiple courses (double-book, >3/day), expand to show all courses
  const rows: ConflictRow[] = [];
  
  breakdown.forEach((c, idx) => {
    const conflictType = c.conflict_type || "unknown";
    const entity = c.student_id || c.entity_id || c.instructor_id || "";
    const day = c.day || "";
    const block = c.block?.toString() || c.block_time || "";
    
    // Get all courses involved in this conflict
    const mainCourse = c.course || "";
    const mainCrn = c.crn?.toString() || "";
    
    // Handle both single conflicting_crn and array conflicting_crns
    const conflictingCrn = c.conflicting_crn ? [c.conflicting_crn] : [];
    const conflictingCrns = c.conflicting_crns || [];
    const allConflictingCrns = [...conflictingCrn, ...conflictingCrns];
    
    // Handle both single conflicting_course and array conflicting_courses
    const conflictingCourse = c.conflicting_course ? [c.conflicting_course] : [];
    const conflictingCourses = c.conflicting_courses || [];
    const allConflictingCourses = [...conflictingCourse, ...conflictingCourses];
    
    // For double-book and >3/day conflicts, create a row for each course involved
    if (
      (conflictType === "student_double_book" || 
       conflictType === "instructor_double_book" ||
       conflictType === "student_gt_max_per_day" ||
       conflictType === "student_gt3_per_day") &&
      (allConflictingCourses.length > 0 || allConflictingCrns.length > 0)
    ) {
      // Collect all courses involved (main + conflicting)
      const allCourses: Array<{ course: string; crn: string }> = [];
      
      // Add main course if it exists
      if (mainCourse || mainCrn) {
        allCourses.push({ course: mainCourse, crn: mainCrn });
      }
      
      // Add conflicting courses
      if (allConflictingCourses.length > 0) {
        allConflictingCourses.forEach((confCourse: string, i: number) => {
          const confCrn = allConflictingCrns[i] ? String(allConflictingCrns[i]) : "";
          allCourses.push({ course: confCourse, crn: confCrn });
        });
      } else if (allConflictingCrns.length > 0) {
        allConflictingCrns.forEach((confCrn: any) => {
          const crnStr = String(confCrn);
          const courseName = crnToCourseMap.get(crnStr) || "";
          allCourses.push({ course: courseName, crn: crnStr });
        });
      }
      
      // Create a row for each course, showing what it conflicts with
      allCourses.forEach((courseInfo, courseIdx) => {
        const otherCourses = allCourses
          .filter((_, i) => i !== courseIdx)
          .map((oc) => oc.course || oc.crn)
          .filter((name) => name);
        
        rows.push({
          id: `conflict-${idx}-course-${courseIdx}`,
          type: conflictType,
          entity: entity,
          day: day,
          block: block,
          course: courseInfo.course,
          crn: courseInfo.crn,
          conflictingCourses: otherCourses,
          size: c.size || null,
          reason: c.reason || null,
          ...c,
          crn: courseInfo.crn,
          course: courseInfo.course,
        });
      });
    } else {
      // For other conflict types, create single row
      const allConflicting = allConflictingCourses.length > 0 
        ? allConflictingCourses 
        : allConflictingCrns.map((cc: any) => String(cc));
      
      rows.push({
        id: `conflict-${idx}`,
        type: conflictType,
        entity: entity,
        day: day,
        block: block,
        course: mainCourse,
        crn: mainCrn,
        conflictingCourses: allConflicting,
        size: c.size || null,
        reason: c.reason || null,
        ...c,
      });
    }
  });

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
