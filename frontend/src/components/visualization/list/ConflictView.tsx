

"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Info, AlertTriangle } from "lucide-react";
import { useExamTable } from "@/lib/hooks/useExamTable";

type ConflictMetrics = {
  hard_student_conflicts: number;
  hard_instructor_conflicts: number;
  students_back_to_back: number;
  large_courses_not_early: number;
  student_gt3_per_day: number;
};

function formatNumber(n: number | null | undefined) {
  if (n == null || Number.isNaN(n)) return "—";
  return n.toLocaleString();
}

function ConflictStat({
  label,
  value,
  description,
  variant = "default",
}: {
  label: string;
  value: number | null | undefined;
  description?: string;
  variant?: "default" | "secondary" | "destructive";
}) {
  return (
    <Card className="shadow-none">
      <CardHeader className="flex items-center justify-between gap-2 p-3">
        <div className="flex items-center gap-2">
          <div className="text-sm font-medium">{label}</div>
          {description ? (
            <span title={description} className="text-muted-foreground">
              <Info className="h-4 w-4" />
            </span>
          ) : null}
        </div>

        <Badge variant={variant as any}>{value == null ? "—" : formatNumber(value)}</Badge>
      </CardHeader>
      <CardContent className="p-0" />
    </Card>
  );
}

function computeAggregatesFromExams(allExams: any[] | undefined): ConflictMetrics {
  const init: ConflictMetrics = {
    hard_student_conflicts: 0,
    hard_instructor_conflicts: 0,
    students_back_to_back: 0,
    large_courses_not_early: 0,
    student_gt3_per_day: 0,
  };

  if (!Array.isArray(allExams)) return init;

  for (const exam of allExams) {
    if (typeof exam.hard_student_conflicts === "number") {
      init.hard_student_conflicts += exam.hard_student_conflicts;
    } else if (exam.hard_student_conflicts) {
      init.hard_student_conflicts += 1;
    }

    if (typeof exam.hard_instructor_conflicts === "number") {
      init.hard_instructor_conflicts += exam.hard_instructor_conflicts;
    } else if (exam.hard_instructor_conflicts) {
      init.hard_instructor_conflicts += 1;
    }

    if (typeof exam.students_back_to_back === "number") {
      init.students_back_to_back += exam.students_back_to_back;
    } else if (exam.students_back_to_back) {
      init.students_back_to_back += 1;
    }

    if (typeof exam.large_courses_not_early === "number") {
      init.large_courses_not_early += exam.large_courses_not_early;
    } else if (exam.large_courses_not_early) {
      init.large_courses_not_early += 1;
    }

    if (typeof exam.student_gt3_per_day === "number") {
      init.student_gt3_per_day += exam.student_gt3_per_day;
    } else if (exam.student_gt3_per_day) {
      init.student_gt3_per_day += 1;
    }
  }

  return init;
}

export default function ConflictView({
  metrics,
}: {
  metrics?: Partial<ConflictMetrics>;
}) {
  const { allExams } = useExamTable();
  const derived = computeAggregatesFromExams(allExams ?? []);

  const merged: ConflictMetrics = {
    hard_student_conflicts: metrics?.hard_student_conflicts ?? derived.hard_student_conflicts,
    hard_instructor_conflicts: metrics?.hard_instructor_conflicts ?? derived.hard_instructor_conflicts,
    students_back_to_back: metrics?.students_back_to_back ?? derived.students_back_to_back,
    large_courses_not_early: metrics?.large_courses_not_early ?? derived.large_courses_not_early,
    student_gt3_per_day: metrics?.student_gt3_per_day ?? derived.student_gt3_per_day,
  };

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-amber-600" />
          Conflict Summary
        </h2>
        <p className="text-sm text-muted-foreground">Quick overview of schedule conflicts</p>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <ConflictStat
          label="Hard student conflicts"
          value={merged.hard_student_conflicts}
          description="Number of student-hard conflicts (must-resolve overlaps)."
          variant="destructive"
        />
        <ConflictStat
          label="Hard instructor conflicts"
          value={merged.hard_instructor_conflicts}
          description="Number of instructor-hard conflicts (instructor double-booked)."
          variant="secondary"
        />
        <ConflictStat
          label="Students back-to-back"
          value={merged.students_back_to_back}
          description="Number of students scheduled back-to-back with no break."
        />
        <ConflictStat
          label="Large courses not early"
          value={merged.large_courses_not_early}
          description="Large courses that are scheduled later than desired (not early)."
        />
        <ConflictStat
          label="Students >3/day"
          value={merged.student_gt3_per_day}
          description="Count of students scheduled for more than 3 exams in a day."
        />
      </div>
    </section>
  );
}
