

"use client";

import { useState } from "react";
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


/*
  Should 3 tabls (like in ViewTabSwitcher)
  the 3 tabs are for 
  1. Students back-to-back
  2. Large courses not early
  3. Courses Not Scheduled

  Each tabe shows a table of exams that contribute to that metric
  back to back : student id, day, block 
  large courses not early: CRN, Course, Size, Day, Block
  courses not scheduled: CRN, Course, Size, Reason

  Use fake data to test the table views
*/



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
  // --- Tabbed table views per file comment ---
  const tabs = [
    { id: "back-to-back", label: "Students back-to-back" },
    { id: "large-not-early", label: "Large courses not early" },
    { id: "not-scheduled", label: "Courses not scheduled" },
  ];

  const [activeTab, setActiveTab] = useState<string>(tabs[0].id);

  // Map exams -> rows for each table. If there's no useful data, return small fake datasets
  function buildRows() {
  const backRows: Array<{ student: string; day: string; block?: string; blocks?: number[] }> = [];
  const largeRows: Array<{ crn: string; course: string; size: number | string; day?: string; block?: string }> = [];
  const notScheduledRows: Array<{ crn: string; course: string; size: number | string; reason: string }> = [];

    if (Array.isArray(allExams) && allExams.length > 0) {
      for (const e of allExams as any[]) {
        // Best-effort extraction using common field names; tolerate missing fields
        const crn = e.crn ?? e.CRN ?? e.id ?? "—";
        const course = e.course_name ?? e.course ?? e.title ?? "—";
        const size = e.enrollment ?? e.size ?? e.students_count ?? "—";
        const day = e.day ?? e.scheduled_day ?? e.date ?? "—";
        const block = e.block ?? e.time_block ?? e.scheduled_block ?? "—";

        if (e.students_back_to_back) {
          // exams don't carry student ids usually; create a row that references the student and count
          backRows.push({ student: e.example_student_id ?? `student(s): ${e.students_back_to_back}`, day, block });
        }

        if (e.large_courses_not_early) {
          largeRows.push({ crn: String(crn), course: String(course), size: Number.isFinite(Number(size)) ? Number(size) : size, day, block });
        }

        // not scheduled: look for common flags
        if (e.scheduled === false || e.not_scheduled || e.unscheduled_reason || e.status === "unscheduled") {
          notScheduledRows.push({ crn: String(crn), course: String(course), size: Number.isFinite(Number(size)) ? Number(size) : size, reason: e.unscheduled_reason ?? "No slot available" });
        }
      }
    }

    // Provide small fake rows if none were discovered (helps local visual testing)
    if (backRows.length === 0) {
      // Students with Back-to-Back Exams
      backRows.push({ student: "1995272", day: "Fri", blocks: [1, 2] });
      backRows.push({ student: "2141168", day: "Fri", blocks: [3, 4] });
      backRows.push({ student: "2158852", day: "Fri", blocks: [0, 1] });
    }

    if (largeRows.length === 0) {
      // Large Courses NOT Scheduled Early (Thu–Sun)
      largeRows.push({ crn: "10284", course: "CS1800", size: 245, day: "Thu", block: "4 (7:00–9:00)" });
      largeRows.push({ crn: "12227", course: "BIOL2217", size: 157, day: "Sun", block: "1 (11:30–1:30)" });
      largeRows.push({ crn: "13326", course: "PSYC4510", size: 151, day: "Thu", block: "3 (4:30–6:30)" });
    }

    if (notScheduledRows.length === 0) {
      // Unassigned Courses
      notScheduledRows.push({ crn: "18421", course: "CS3100", size: 160, reason: "student_double_book: 34, instructor_double_book: 1" });
      notScheduledRows.push({ crn: "14982", course: "CHEM2313", size: 149, reason: "student_double_book: 35" });
    }

    return { backRows, largeRows, notScheduledRows };
  }

  const { backRows, largeRows, notScheduledRows } = buildRows();

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

      {/* Tabs */}
      <div className="mt-4">
        <div className="flex gap-2">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`rounded-md px-3 py-1 text-sm font-medium transition-colors ${
                activeTab === t.id
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground hover:bg-muted/80"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div className="mt-3">
          {activeTab === "back-to-back" && (
            <Card>
              <CardHeader>
                <CardTitle>Students back-to-back</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-auto">
                  <table className="w-full table-auto text-sm">
                    <thead>
                      <tr className="text-left text-muted-foreground">
                        <th className="px-2 py-2">Student</th>
                        <th className="px-2 py-2">Day</th>
                        <th className="px-2 py-2">Block(s)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {backRows.map((r, i) => (
                        <tr key={i} className="border-t">
                          <td className="px-2 py-2">{r.student}</td>
                          <td className="px-2 py-2">{r.day}</td>
                          <td className="px-2 py-2">{r.blocks ? r.blocks.join(", ") : r.block ?? "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}

          {activeTab === "large-not-early" && (
            <Card>
              <CardHeader>
                <CardTitle>Large courses not early</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-auto">
                  <table className="w-full table-auto text-sm">
                    <thead>
                      <tr className="text-left text-muted-foreground">
                        <th className="px-2 py-2">CRN</th>
                        <th className="px-2 py-2">Course</th>
                        <th className="px-2 py-2">Size</th>
                        <th className="px-2 py-2">Day</th>
                        <th className="px-2 py-2">Block</th>
                      </tr>
                    </thead>
                    <tbody>
                      {largeRows.map((r, i) => (
                        <tr key={i} className="border-t">
                          <td className="px-2 py-2">{r.crn}</td>
                          <td className="px-2 py-2">{r.course}</td>
                          <td className="px-2 py-2">{r.size}</td>
                          <td className="px-2 py-2">{r.day ?? "—"}</td>
                          <td className="px-2 py-2">{r.block ?? "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}

          {activeTab === "not-scheduled" && (
            <Card>
              <CardHeader>
                <CardTitle>Courses not scheduled</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-auto">
                  <table className="w-full table-auto text-sm">
                    <thead>
                      <tr className="text-left text-muted-foreground">
                        <th className="px-2 py-2">CRN</th>
                        <th className="px-2 py-2">Course</th>
                        <th className="px-2 py-2">Size</th>
                        <th className="px-2 py-2">Reason</th>
                      </tr>
                    </thead>
                    <tbody>
                      {notScheduledRows.map((r, i) => (
                        <tr key={i} className="border-t">
                          <td className="px-2 py-2">{r.crn}</td>
                          <td className="px-2 py-2">{r.course}</td>
                          <td className="px-2 py-2">{r.size}</td>
                          <td className="px-2 py-2">{r.reason}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </section>
  );
}
