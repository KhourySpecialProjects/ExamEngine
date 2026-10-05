import {
  AlertTriangle,
  BookOpen,
  Briefcase,
  Calendar,
  Clock,
  User,
  Users,
  UserX,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

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
 * Conflict types the backend emits, in display order: student types first,
 * then instructor types, then course-level types. Drives the tab order and
 * the definitions legend; unlisted types sort after these.
 */
export const CONFLICT_TYPE_ORDER = [
  "student_double_book",
  "student_gt_max_per_day",
  "back_to_back",
  "instructor_double_book",
  "instructor_gt_max_per_day",
  "back_to_back_instructor",
  "large_course_not_early",
];

/** Sort key for CONFLICT_TYPE_ORDER; unlisted types rank last. */
export function conflictTypeRank(type: string): number {
  const i = CONFLICT_TYPE_ORDER.indexOf(type);
  return i === -1 ? CONFLICT_TYPE_ORDER.length : i;
}

// Labels start with who is affected ("Student …" / "Instructor …").
// back_to_back is the backend's type for students.
export const conflictTypeMap: Record<string, string> = {
  student_double_book: "Student Double-Book",
  student_gt_max_per_day: "Student Per-Day Limit",
  student_gt3_per_day: "Student 3+ Exams Per Day",
  back_to_back: "Student Back-to-Back",
  back_to_back_student: "Student Back-to-Back",
  instructor_double_book: "Instructor Double-Book",
  instructor_gt_max_per_day: "Instructor Per-Day Limit",
  back_to_back_instructor: "Instructor Back-to-Back",
  large_course_not_early: "Large Course Not Early",
  unknown: "Uncategorized",
};

export const conflictDescriptions: Record<string, string> = {
  student_double_book:
    "A student is scheduled for more than one exam at the same time. Requires resolution.",
  student_gt_max_per_day:
    "A student has more exams in one day than the configured maximum.",
  student_gt3_per_day:
    "Students scheduled for more than 3 exams in a single day.",
  back_to_back:
    "A student has exams in consecutive time blocks on the same day.",
  back_to_back_student:
    "A student has exams in consecutive time blocks on the same day.",
  instructor_double_book:
    "An instructor is scheduled to proctor/teach more than one exam at the same time.",
  instructor_gt_max_per_day:
    "An instructor has more exams in one day than the configured maximum.",
  back_to_back_instructor:
    "An instructor has exams in consecutive time blocks on the same day.",
  large_course_not_early:
    "Courses with 100+ students scheduled Thursday or later in the week.",
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
  if (t.includes("instructor_gt_max_per_day"))
    return <AlertTriangle className="w-4 h-4 text-amber-600" />;
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
export type ConflictAudience = "Student" | "Instructor" | "Course";

const audienceStyles: Record<ConflictAudience, string> = {
  Student: "border-sky-200 bg-sky-50 text-sky-900",
  Instructor: "border-violet-200 bg-violet-50 text-violet-900",
  Course: "border-slate-200 bg-slate-50 text-slate-700",
};

interface Props {
  label: string;
  /** Who the conflict affects, shown as a pill under the title. */
  audience?: ConflictAudience;
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
  audience,
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
      {/* Icon sits on the pill row so the title gets the full card width;
          px-3 (not the Card default px-6) keeps titles on one line when all
          seven cards share a row. */}
      <CardHeader className="flex flex-col gap-1.5 space-y-0 px-3 pb-2">
        <CardTitle className="text-sm font-medium">{label}</CardTitle>
        <div className="flex w-full items-center justify-between gap-2">
          {audience && (
            <Badge variant="outline" className={audienceStyles[audience]}>
              {audience}
            </Badge>
          )}
          {icon}
        </div>
      </CardHeader>
      <CardContent className="px-3">
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
