import {
  AlertTriangle,
  BookOpen,
  Briefcase,
  Calendar,
  Clock,
  GraduationCap,
  User,
  Users,
  UserX,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ConflictMetrics } from "@/lib/types/conflict.types";

import { cn } from "@/lib/utils";

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
export function computeAggregatesFromExams(
  allExams: any[] | undefined,
): ConflictMetrics {
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
      typeof exam.hard_student_conflicts === "number"
        ? exam.hard_student_conflicts
        : exam.hard_student_conflicts
          ? 1
          : 0;
    init.hard_instructor_conflicts +=
      typeof exam.hard_instructor_conflicts === "number"
        ? exam.hard_instructor_conflicts
        : exam.hard_instructor_conflicts
          ? 1
          : 0;

    init.students_back_to_back +=
      typeof exam.students_back_to_back === "number"
        ? exam.students_back_to_back
        : exam.students_back_to_back
          ? 1
          : 0;
    init.instructors_back_to_back +=
      typeof exam.instructors_back_to_back === "number"
        ? exam.instructors_back_to_back
        : exam.instructors_back_to_back || exam.back_to_back_instructor
          ? 1
          : 0;

    init.large_courses_not_early +=
      typeof exam.large_courses_not_early === "number"
        ? exam.large_courses_not_early
        : exam.large_courses_not_early
          ? 1
          : 0;

    init.student_gt3_per_day +=
      typeof exam.student_gt3_per_day === "number"
        ? exam.student_gt3_per_day
        : exam.student_gt3_per_day
          ? 1
          : 0;
  }

  return init;
}

/**
 * Compute aggregated totals from the backend `breakdown` array.
 * This prefers explicit numeric counts when available and applies
 * special handling for back-to-back and "over max" student rules.
 */
export function computeTotalsFromBreakdown(
  bd: any[] | undefined,
): ConflictMetrics {
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
      init.hard_student_conflicts +=
        typeof c.student_conflicts === "number"
          ? c.student_conflicts
          : typeof c.count === "number"
            ? c.count
            : 1;
    }
    if (type === "instructor_double_book") {
      init.hard_instructor_conflicts +=
        typeof c.instructor_conflicts === "number"
          ? c.instructor_conflicts
          : typeof c.count === "number"
            ? c.count
            : 1;
    }

    if (
      BACK_TO_BACK_GENERIC.has(type) ||
      BACK_TO_BACK_STUDENT.has(type) ||
      BACK_TO_BACK_INSTRUCTOR.has(type)
    ) {
      const studentCount =
        typeof c.student_conflicts === "number"
          ? c.student_conflicts
          : BACK_TO_BACK_STUDENT.has(type) || BACK_TO_BACK_GENERIC.has(type)
            ? typeof c.count === "number"
              ? c.count
              : 1
            : 0;
      const instructorCount =
        typeof c.instructor_conflicts === "number"
          ? c.instructor_conflicts
          : BACK_TO_BACK_INSTRUCTOR.has(type) || BACK_TO_BACK_GENERIC.has(type)
            ? typeof c.count === "number"
              ? c.count
              : 0
            : 0;

      init.students_back_to_back += studentCount;
      init.instructors_back_to_back += instructorCount;
    }

    if (type === "large_course_not_early" || c.large_courses_not_early) {
      init.large_courses_not_early += 1;
    }

    if (
      [
        "student_gt_max_per_day",
        "student_gt3_per_day",
        "student_gt_max",
      ].includes(type)
    ) {
      init.student_gt3_per_day +=
        typeof c.student_conflicts === "number"
          ? c.student_conflicts
          : typeof c.count === "number"
            ? c.count
            : 1;
    }
  }

  return init;
}

export const conflictTypeMap: Record<string, string> = {
  student_double_book: "Student Double-Book",
  student_gt_max_per_day: "Student Per-Day Limit",
  student_gt3_per_day: "Student has more than 2 exams per day",
  instructor_double_book: "Instructor Double-Book",
  back_to_back: "Back-to-Back",
  back_to_back_student: "Back-to-Back (Students)",
  back_to_back_instructor: "Back-to-Back (Instructors)",
  large_course_not_early: "Large Course Not Early",
  unknown: "Uncategorized",
};

export const conflictDescriptions: Record<string, string> = {
  student_double_book:
    "A student is scheduled for more than one exam at the same time. Requires resolution.",
  instructor_double_book:
    "An instructor is scheduled to proctor/teach more than one exam at the same time.",
  back_to_back:
    "Exams scheduled back-to-back for the same entity (student/instructor) with no gap.",
  back_to_back_student:
    "A student has two exams scheduled in immediately consecutive blocks.",
  back_to_back_instructor:
    "An instructor has back-to-back assignments with no break.",
  large_course_not_early:
    "Large-enrollment courses that are not scheduled in earlier (preferred) time slots.",
  student_gt3_per_day:
    "Students scheduled for more than 3 exams in a single day.",
  student_gt_max_per_day:
    "Students exceeding the configured maximum exams per day.",
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
  if (t.includes("student_double_book"))
    return <User className="w-4 h-4 text-rose-600" />;
  if (t.includes("instructor_double_book"))
    return <Users className="w-4 h-4 text-amber-600" />;
  if (
    t.includes("back_to_back_student") ||
    t.includes("back_to_back_instructor") ||
    t === "back_to_back"
  )
    return <Clock className="w-4 h-4 text-sky-600" />;
  if (t.includes("large_course_not_early"))
    return <BookOpen className="w-4 h-4 text-indigo-600" />;
  if (
    t.includes("student_gt3") ||
    t.includes("student_gt_max") ||
    t.includes("student_gt_max_per_day") ||
    t.includes("student_gt")
  )
    return <AlertTriangle className="w-4 h-4 text-rose-600" />;
  if (t.includes("student") && !t.includes("double"))
    return <User className="w-4 h-4 text-rose-600" />;
  if (t.includes("instructor") && !t.includes("double"))
    return <Users className="w-4 h-4 text-amber-600" />;
  return <Calendar className="w-4 h-4 text-foreground" />;
}
/**
 * Small presentational card that shows a single conflict metric.
 * Styled consistently with StatCard from StatsOverview.
 */
interface Props {
  label: string;
  value: number | null | undefined;
  subtitle?: string;
  icon?: React.ReactNode;
  variant?: "default" | "warning" | "success" | "destructive" | "secondary";
}

const variantConfig = {
  default: {
    icon: "text-primary",
    accent: "bg-primary/10",
    border: "hover:border-primary/30",
  },
  warning: {
    icon: "text-amber-600",
    accent: "bg-amber-500/10",
    border: "hover:border-amber-500/30",
  },
  destructive: {
    icon: "text-destructive",
    accent: "bg-destructive/10",
    border: "hover:border-destructive/30",
  },
  success: {
    icon: "text-green-600",
    accent: "bg-green-500/10",
    border: "hover:border-green-500/30",
  },
  secondary: {
    icon: "text-secondary-foreground",
    accent: "bg-secondary/50",
    border: "hover:border-secondary/30",
  },
};

export function ConflictStat({
  label,
  value,
  subtitle,
  icon,
  variant = "default",
}: Props) {
  const styles = variantConfig[variant] ?? variantConfig.default;
  const hasConflicts = value != null && value > 0;

  return (
    <Card
      className={cn(
        "transition-all duration-200 hover:shadow-md",
        styles.border,
      )}
    >
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{label}</CardTitle>
        {icon}
      </CardHeader>
      <CardContent>
        <div
          className={cn(
            "text-3xl font-bold tracking-tight",
            hasConflicts && variant === "destructive" && "text-destructive",
            hasConflicts && variant === "warning" && "text-amber-600",
            !hasConflicts && variant !== "default" && "text-green-600",
          )}
        >
          {value == null ? "—" : formatNumber(value)}
        </div>
        {subtitle && (
          <p className="text-xs text-muted-foreground mt-1.5">{subtitle}</p>
        )}
      </CardContent>
    </Card>
  );
}

// Pre-configured conflict stat cards for common use cases
export const conflictStatPresets = {
  studentDoubleBook: (value: number | null | undefined) => ({
    label: "Double Booked",
    value,
    subtitle: "Students with overlapping exams",
    icon: <UserX className="h-4 w-4" />,
    variant: (value ?? 0) > 0 ? "destructive" : "success",
  }),
  instructorDoubleBook: (value: number | null | undefined) => ({
    label: "Instructor Conflicts",
    value,
    subtitle: "Instructors with overlapping exams",
    icon: <Briefcase className="h-4 w-4" />,
    variant: (value ?? 0) > 0 ? "destructive" : "success",
  }),
  studentMaxPerDay: (value: number | null | undefined) => ({
    label: "Overloaded Days",
    value,
    subtitle: "Students with 3+ exams in one day",
    icon: <Calendar className="h-4 w-4" />,
    variant: (value ?? 0) > 0 ? "destructive" : "success",
  }),
  backToBack: (value: number | null | undefined) => ({
    label: "Back-to-Back",
    value,
    subtitle: "Consecutive exam occurrences",
    icon: <Clock className="h-4 w-4" />,
    variant: (value ?? 0) > 0 ? "warning" : "success",
  }),
  totalHard: (value: number | null | undefined) => ({
    label: "Hard Conflicts",
    value,
    subtitle: "Must be resolved before publish",
    icon: <AlertTriangle className="h-4 w-4" />,
    variant: (value ?? 0) > 0 ? "destructive" : "success",
  }),
  totalSoft: (value: number | null | undefined) => ({
    label: "Soft Conflicts",
    value,
    subtitle: "Recommended to minimize",
    icon: <Users className="h-4 w-4" />,
    variant: (value ?? 0) > 0 ? "warning" : "success",
  }),
} as const;
