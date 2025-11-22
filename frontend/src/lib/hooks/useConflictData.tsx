import { ConflictMetrics } from "@/lib/types/conflict.types";
import { User, Users, Clock, Calendar, AlertTriangle, BookOpen } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export const PAGE_SIZE = 10;

/**
 * Format a number for display in the UI.
 * - returns an em-dash for null/undefined/NaN
 * - otherwise returns the locale-aware string for the number
 */
function formatNumber(n: number | null | undefined) {
  if (n == null || Number.isNaN(n)) return "—";
  return n.toLocaleString();
}


/**
 * Compute aggregated conflict metrics from the local `allExams` array.
 * This is a best-effort summarizer used when the backend breakdown is not present.
 * It tolerates multiple possible field names and numeric-or-boolean encodings.
 */
export function computeAggregatesFromExams(allExams: any[] | undefined): ConflictMetrics {
  const init: ConflictMetrics = {
    hard_student_conflicts: 0,
    hard_instructor_conflicts: 0,
    students_back_to_back: 0,
    instructors_back_to_back: 0,
    large_courses_not_early: 0,
    student_gt3_per_day: 0,
  };

  if (!Array.isArray(allExams)) return init;

  for (const exam of allExams) {
    init.hard_student_conflicts +=
      typeof exam.hard_student_conflicts === "number" ? exam.hard_student_conflicts : exam.hard_student_conflicts ? 1 : 0;
    init.hard_instructor_conflicts +=
      typeof exam.hard_instructor_conflicts === "number" ? exam.hard_instructor_conflicts : exam.hard_instructor_conflicts ? 1 : 0;

    init.students_back_to_back +=
      typeof exam.students_back_to_back === "number" ? exam.students_back_to_back : exam.students_back_to_back ? 1 : 0;
    init.instructors_back_to_back +=
      typeof exam.instructors_back_to_back === "number" ? exam.instructors_back_to_back : (exam.instructors_back_to_back || exam.back_to_back_instructor) ? 1 : 0;

    init.large_courses_not_early +=
      typeof exam.large_courses_not_early === "number" ? exam.large_courses_not_early : exam.large_courses_not_early ? 1 : 0;

    init.student_gt3_per_day +=
      typeof exam.student_gt3_per_day === "number" ? exam.student_gt3_per_day : exam.student_gt3_per_day ? 1 : 0;
  }

  return init;
}

/**
 * Compute aggregated totals from the backend `breakdown` array.
 * This prefers explicit numeric counts when available and applies
 * special handling for back-to-back and "over max" student rules.
 */
export function computeTotalsFromBreakdown(bd: any[] | undefined): ConflictMetrics {
  const init: ConflictMetrics = {
    hard_student_conflicts: 0,
    hard_instructor_conflicts: 0,
    students_back_to_back: 0,
    instructors_back_to_back: 0,
    large_courses_not_early: 0,
    student_gt3_per_day: 0,
  };
  if (!Array.isArray(bd) || bd.length === 0) return init;

  const BACK_TO_BACK_GENERIC = new Set(["back_to_back"]);
  const BACK_TO_BACK_STUDENT = new Set(["back_to_back_student"]);
  const BACK_TO_BACK_INSTRUCTOR = new Set(["back_to_back_instructor"]);

  for (const c of bd as any[]) {
    const type = c.conflict_type ?? c.violation ?? "unknown";

    if (type === "student_double_book") {
      init.hard_student_conflicts += (typeof c.student_conflicts === "number" ? c.student_conflicts : (typeof c.count === "number" ? c.count : 1));
    }
    if (type === "instructor_double_book") {
      init.hard_instructor_conflicts += (typeof c.instructor_conflicts === "number" ? c.instructor_conflicts : (typeof c.count === "number" ? c.count : 1));
    }

    if (BACK_TO_BACK_GENERIC.has(type) || BACK_TO_BACK_STUDENT.has(type) || BACK_TO_BACK_INSTRUCTOR.has(type)) {
      const studentCount = typeof c.student_conflicts === "number" ? c.student_conflicts : (BACK_TO_BACK_STUDENT.has(type) || BACK_TO_BACK_GENERIC.has(type) ? (typeof c.count === "number" ? c.count : 1) : 0);
      const instructorCount = typeof c.instructor_conflicts === "number" ? c.instructor_conflicts : (BACK_TO_BACK_INSTRUCTOR.has(type) || BACK_TO_BACK_GENERIC.has(type) ? (typeof c.count === "number" ? c.count : 0) : 0);

      init.students_back_to_back += studentCount;
      init.instructors_back_to_back += instructorCount;
    }

    if (type === "large_course_not_early" || c.large_courses_not_early) {
      init.large_courses_not_early += 1;
    }

    if (["student_gt_max_per_day", "student_gt3_per_day", "student_gt_max"].includes(type)) {
      init.student_gt3_per_day += (typeof c.student_conflicts === "number" ? c.student_conflicts : (typeof c.count === "number" ? c.count : 1));
    }
  }

  return init;
}

export const conflictTypeMap: Record<string, string> = {
    student_double_book: "Student Double-Book",
    student_gt_max_per_day: "Student Per-Day Limit",
    student_gt3_per_day: "Student >3/day",
    instructor_double_book: "Instructor Double-Book",
    back_to_back: "Back-to-Back",
    back_to_back_student: "Back-to-Back (Students)",
    back_to_back_instructor: "Back-to-Back (Instructors)",
    large_course_not_early: "Large Course Not Early",
    unknown: "Uncategorized",
  };

export const conflictDescriptions: Record<string, string> = {
    student_double_book: "A student is scheduled for more than one exam at the same time. Requires resolution.",
    instructor_double_book: "An instructor is scheduled to proctor/teach more than one exam at the same time.",
    back_to_back: "Exams scheduled back-to-back for the same entity (student/instructor) with no gap.",
    back_to_back_student: "A student has two exams scheduled in immediately consecutive blocks.",
    back_to_back_instructor: "An instructor has back-to-back assignments with no break.",
    large_course_not_early: "Large-enrollment courses that are not scheduled in earlier (preferred) time slots.",
    student_gt3_per_day: "Students scheduled for more than 3 exams in a single day.",
    student_gt_max_per_day: "Students exceeding the configured maximum exams per day.",
    unknown: "Uncategorized or unknown conflict type.",
  };

export const dayNameMap: Record<string, string> = {
    Mon: "Monday",
    Tue: "Tuesday",
    Wed: "Wednesday",
    Thu: "Thursday",
    Fri: "Friday",
    Sat: "Saturday",
    Sun: "Sunday",
  };

export function getIconForType(type: string) {
    if (!type) return null;
    const t = String(type).toLowerCase();
    if (t.includes("student_double_book")) return <User className="w-4 h-4 text-rose-600" />;
    if (t.includes("instructor_double_book")) return <Users className="w-4 h-4 text-amber-600" />;
    if (t.includes("back_to_back_student") || t.includes("back_to_back_instructor") || t === "back_to_back") return <Clock className="w-4 h-4 text-sky-600" />;
    if (t.includes("large_course_not_early")) return <BookOpen className="w-4 h-4 text-indigo-600" />;
    if (t.includes("student_gt3") || t.includes("student_gt_max") || t.includes("student_gt_max_per_day") || t.includes("student_gt")) return <AlertTriangle className="w-4 h-4 text-rose-600" />;
    if (t.includes("student") && !t.includes("double")) return <User className="w-4 h-4 text-rose-600" />;
    if (t.includes("instructor") && !t.includes("double")) return <Users className="w-4 h-4 text-amber-600" />;
    return <Calendar className="w-4 h-4 text-foreground" />;
  };

/**
 * Small presentational card that shows a single conflict metric.
 * - `label`: human readable metric title
 * - `value`: numeric metric value (nullable)
 * - `variant` / `badgeClassName`: visual styling hooks
 */
export function ConflictStat({
  label,
  value,
  description,
  variant = "default",
  badgeClassName,
}: {
  label: string;
  value: number | null | undefined;
  description?: string;
  variant?: "default" | "secondary" | "destructive";
  badgeClassName?: string;
}) {
  return (
    <Card className="shadow-none">
      <CardHeader className="flex items-center justify-between gap-2 p-3">
        <div className="flex items-center gap-2">
          <div className="text-sm md:text-base font-medium">{label}</div>
        </div>

        <Badge variant={variant as any} className={`px-2 py-1 ${badgeClassName ?? ""}`}>
          <span className="text-base md:text-lg font-semibold">{value == null ? "—" : formatNumber(value)}</span>
        </Badge>
      </CardHeader>
      <CardContent className="p-0" />
    </Card>
  );
};