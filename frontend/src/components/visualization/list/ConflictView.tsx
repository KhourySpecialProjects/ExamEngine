"use client";

// header icon removed
import { useState } from "react";
import { User, Users, Clock, Calendar, AlertTriangle, BookOpen } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useExamTable } from "@/lib/hooks/useExamTable";
import { useScheduleStore } from "@/lib/store/scheduleStore";
import { mapConflictsToRows } from "@/lib/utils";

type ConflictMetrics = {
  hard_student_conflicts: number;
  hard_instructor_conflicts: number;
  students_back_to_back: number;
  instructors_back_to_back: number;
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
}

function computeAggregatesFromExams(
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

    if (typeof exam.instructors_back_to_back === "number") {
      init.instructors_back_to_back += exam.instructors_back_to_back;
    } else if (exam.instructors_back_to_back || exam.back_to_back_instructor) {
      init.instructors_back_to_back += 1;
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
  const currentSchedule = useScheduleStore((s) => s.currentSchedule);
  const breakdown = currentSchedule?.conflicts?.breakdown ?? [];
  // Compute totals directly from backend breakdown for more accurate summary
  function computeTotalsFromBreakdown(bd: any[] | undefined): ConflictMetrics {
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

      // Back-to-back handling: prefer explicit student/instructor counts when available
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

  const mappedTotals: ConflictMetrics = computeTotalsFromBreakdown(breakdown);

  const merged: ConflictMetrics = {
    hard_student_conflicts:
      metrics?.hard_student_conflicts ?? (mappedTotals.hard_student_conflicts > 0 ? mappedTotals.hard_student_conflicts : derived.hard_student_conflicts),
    hard_instructor_conflicts:
      metrics?.hard_instructor_conflicts ?? (mappedTotals.hard_instructor_conflicts > 0 ? mappedTotals.hard_instructor_conflicts : derived.hard_instructor_conflicts),
    students_back_to_back:
      metrics?.students_back_to_back ?? (mappedTotals.students_back_to_back > 0 ? mappedTotals.students_back_to_back : derived.students_back_to_back),
    instructors_back_to_back:
      metrics?.instructors_back_to_back ?? (mappedTotals.instructors_back_to_back > 0 ? mappedTotals.instructors_back_to_back : derived.instructors_back_to_back),
    large_courses_not_early:
      metrics?.large_courses_not_early ?? derived.large_courses_not_early,
    student_gt3_per_day:
      metrics?.student_gt3_per_day ?? (mappedTotals.student_gt3_per_day > 0 ? mappedTotals.student_gt3_per_day : derived.student_gt3_per_day),
  };
  // --- Tabbed table views per file comment ---
  // tabs will be built dynamically from backend conflict types later

  // activeTab will be initialized after we compute effectiveTabs

  // Map exams -> rows for each table. If there's no useful data, return small fake datasets
  function buildRows() {
    const backRows: Array<{
      student: string;
      day: string;
      block?: string;
      blocks?: number[];
    }> = [];
    const largeRows: Array<{
      crn: string;
      course: string;
      size: number | string;
      day?: string;
      block?: string;
    }> = [];

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
          backRows.push({
            student:
              e.example_student_id ?? `student(s): ${e.students_back_to_back}`,
            day,
            block,
          });
        }

        if (e.large_courses_not_early) {
          largeRows.push({
            crn: String(crn),
            course: String(course),
            size: Number.isFinite(Number(size)) ? Number(size) : size,
            day,
            block,
          });
        }

        // algorithm schedules all classes; skip unscheduled handling
      }
    }

    // No fake rows — if no data is present, tables will simply show empty state.

    return { backRows, largeRows };
  }

  const { backRows, largeRows } = buildRows();

  // Prefer rows built from backend conflicts when available
  const mappedRows = mapConflictsToRows(allExams ?? [], breakdown ?? []);
  const displayBackRows = (mappedRows.backRows && mappedRows.backRows.length > 0) ? mappedRows.backRows : backRows;
  const displayLargeRows = (mappedRows.largeRows && mappedRows.largeRows.length > 0) ? mappedRows.largeRows : largeRows;
  // Build rows per conflict type from backend breakdown (dynamic tabs)
  const conflictTypeMap: Record<string, string> = {
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
  // Build rows grouped by conflict type from breakdown, with fallbacks to exams data
  const conflictTypeRows: Record<string, any[]> = {};

 
  const conflictDescriptions: Record<string, string> = {
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

  function getIconForType(type: string) {
    // Map specific conflict types to distinct icons/colors
    if (!type) return null;
    const t = String(type).toLowerCase();

    if (t.includes("student_double_book")) return <User className="w-4 h-4 text-rose-600" />;
    if (t.includes("instructor_double_book")) return <Users className="w-4 h-4 text-amber-600" />;
    if (t.includes("back_to_back_student") || t.includes("back_to_back_instructor") || t === "back_to_back") return <Clock className="w-4 h-4 text-sky-600" />;
    if (t.includes("large_course_not_early")) return <BookOpen className="w-4 h-4 text-indigo-600" />;
    if (t.includes("student_gt3") || t.includes("student_gt_max") || t.includes("student_gt_max_per_day") || t.includes("student_gt")) return <AlertTriangle className="w-4 h-4 text-rose-600" />;
    if (t.includes("student") && !t.includes("double")) return <User className="w-4 h-4 text-rose-600" />;
    if (t.includes("instructor") && !t.includes("double")) return <Users className="w-4 h-4 text-amber-600" />;

    // fallback
    return <Calendar className="w-4 h-4 text-foreground" />;
  }

  const findExamByCrn = (crn: any) => {
    if (!crn) return null;
    return (allExams ?? []).find((e: any) => String(e.crn ?? e.CRN ?? e.id) === String(crn));
  };

  for (const conf of (breakdown ?? []) as any[]) {
    const type = conf.conflict_type ?? conf.violation ?? "unknown";
    conflictTypeRows[type] = conflictTypeRows[type] ?? [];

    const rawCrn = conf.crn ?? (Array.isArray(conf.conflicting_crns) ? conf.conflicting_crns[0] : conf.conflicting_crn) ?? null;
  const exam: any = findExamByCrn(rawCrn);

    const crnVal = rawCrn ?? (exam ? String(exam.crn ?? exam.CRN ?? exam.id) : null);
    const courseVal = conf.course ?? conf.conflicting_course ?? (exam ? (exam.course_name ?? exam.course ?? exam.title) : null) ?? (Array.isArray(conf.conflicting_courses) ? conf.conflicting_courses[0] : null);

  const sizeVal = exam ? (exam.enrollment ?? exam.size ?? exam.students_count ?? null) : null;

    const entityVal = conf.student_id ? `S:${conf.student_id}` : conf.instructor_id ? `I:${conf.instructor_id}` : conf.entity_id ?? null;

    let blockVal = null;
    if (Array.isArray(conf.blocks)) blockVal = conf.blocks.join(", ");
    else if (conf.block_time) blockVal = conf.block_time;
    else if (conf.block) blockVal = conf.block;

    let conflictingCourses: string[] = [];
    if (Array.isArray(conf.conflicting_courses)) conflictingCourses = conf.conflicting_courses.map((c: any) => String(c));
    else if (Array.isArray(conf.conflicting_crns)) conflictingCourses = conf.conflicting_crns.map((c: any) => String(c));
    else if (typeof conf.conflicting_courses === "string") conflictingCourses = [conf.conflicting_courses];

    const row = {
      entity: entityVal,
      type,
      day: conf.day ?? conf.block_day ?? null,
      block: blockVal,
      size: sizeVal,
      course: courseVal,
      crn: crnVal,
      conflicting_courses: conflictingCourses,
      reason: conf.unscheduled_reason ?? conf.reason ?? null,
      raw: conf,
    };

    conflictTypeRows[type].push(row);
  }

  const dynamicTabEntries = Object.keys(conflictTypeRows).length > 0
    ? Object.keys(conflictTypeRows).map((t) => ({ id: t, label: conflictTypeMap[t] ?? t }))
    : [
        { id: "back_to_back", label: "Back-to-Back" },
        { id: "large_course_not_early", label: "Large courses not early" },
      ];

  // replace tabs with dynamic entries
  const effectiveTabs = dynamicTabEntries;

  // pagination state per active tab
  const PAGE_SIZE = 10;
  const [pageByTab, setPageByTab] = useState<Record<string, number>>({});

  function setPage(tabId: string, page: number) {
    setPageByTab((s) => ({ ...s, [tabId]: page }));
  }

  function getPage(tabId: string) {
    return pageByTab[tabId] ?? 0;
  }

  // active tab state (initialize to first dynamic tab)
  const [activeTab, setActiveTab] = useState<string>(effectiveTabs[0]?.id ?? "back_to_back");

  return (
    <section className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">Conflict View</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Quick overview of schedule conflicts
        </p>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-6">
        <ConflictStat
          label="Student Double-Book"
          value={merged.hard_student_conflicts}
          description="Number of student double-book conflicts (must-resolve overlaps)."
          variant="destructive"
        />
        <ConflictStat
          label="Instructor Double-Book"
          value={merged.hard_instructor_conflicts}
          description="Number of instructor double-book conflicts (instructor double-booked)."
          variant="destructive"
        />
        <ConflictStat
          label="Student >3/day"
          value={merged.student_gt3_per_day}
          description="Count of students scheduled for more than 3 exams in a day."
          variant="destructive"
        />
        <ConflictStat
          label="Students Back-to-Back"
          value={merged.students_back_to_back}
          description="Number of students scheduled back-to-back with no break."
          badgeClassName="bg-amber-600 text-white"
        />
        <ConflictStat
          label="Instructors Back-to-Back"
          value={merged.instructors_back_to_back}
          description="Number of instructors scheduled back-to-back with no break."
          badgeClassName="bg-amber-600 text-white"
        />
        <ConflictStat
          label="Large Course Not Early"
          value={merged.large_courses_not_early}
          description="Large courses that are scheduled later than desired (not early)."
          badgeClassName="bg-amber-600 text-white"
        />
      </div>

      {/* Tabs */}
      <div className="mt-4">
        <div className="flex gap-2">
          {effectiveTabs.map((t) => (
            <Button
              key={t.id}
              onClick={() => {
                setActiveTab(t.id);
                setPage(t.id, 0);
              }}
              className={`rounded-md px-3 py-1 text-sm font-medium transition-colors ${
                activeTab === t.id
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground hover:bg-muted/80"
              }`}
            >
              {t.label}
            </Button>
          ))}
        </div>

        <div className="mt-3">
          {/* Generic table for the active conflict type */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <span className="inline-flex items-center">{getIconForType(activeTab)}</span>
                <span>{effectiveTabs.find((x) => x.id === activeTab)?.label ?? "Conflicts"}</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-auto">
                {(() => {
                  const rowsForActive = conflictTypeRows[activeTab] ?? (activeTab === "back_to_back" ? displayBackRows : activeTab === "large_course_not_early" ? displayLargeRows : []);
                  const page = getPage(activeTab);
                  const totalPages = Math.max(1, Math.ceil(rowsForActive.length / PAGE_SIZE));
                  const start = page * PAGE_SIZE;
                  const end = Math.min(rowsForActive.length, start + PAGE_SIZE);

                  // Determine which columns actually have data for these rows.
                  const has = {
                    entity: rowsForActive.some((r: any) => r.entity != null && String(r.entity).trim() !== ""),
                    day: rowsForActive.some((r: any) => r.day != null && String(r.day).trim() !== ""),
                    block: rowsForActive.some((r: any) => (Array.isArray(r.blocks) ? r.blocks.length > 0 : (r.block != null && String(r.block).trim() !== ""))),
                    course: rowsForActive.some((r: any) => r.course != null && String(r.course).trim() !== ""),
                    crn: rowsForActive.some((r: any) => r.crn != null && String(r.crn).trim() !== ""),
                    conflicting_courses: rowsForActive.some((r: any) => Array.isArray(r.conflicting_courses) ? r.conflicting_courses.length > 0 : (r.conflicting_courses != null && String(r.conflicting_courses).trim() !== "")),
                    reason: rowsForActive.some((r: any) => r.reason != null && String(r.reason).trim() !== ""),
                    size: rowsForActive.some((r: any) => r.size != null && String(r.size).trim() !== ""),
                  };

                  // Special-case large_course_not_early: hide block, conflicting courses and reason per request
                  if (activeTab === "large_course_not_early") {
                    has.block = false;
                    has.conflicting_courses = false;
                    has.reason = false;
                  }

                  const columns: Array<{ key: string; label: string }> = [];
                  if (has.entity) columns.push({ key: "entity", label: "Entity" });
                  if (has.day) columns.push({ key: "day", label: "Day" });
                  if (has.block) columns.push({ key: "block", label: "Block" });
                  if (has.course) columns.push({ key: "course", label: "Course" });
                  if (has.crn) columns.push({ key: "crn", label: "CRN" });
                  if (has.size) columns.push({ key: "size", label: "Size" });
                  if (has.conflicting_courses) columns.push({ key: "conflicting_courses", label: "Conflicting Courses" });
                  if (has.reason) columns.push({ key: "reason", label: "Reason" });

                  return (
                    <>
                      <table className="w-full table-auto text-sm">
                        <thead>
                          <tr className="text-left text-muted-foreground">
                            {columns.map((c) => (
                              <th key={c.key} className="px-2 py-2">{c.label}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {rowsForActive.slice(start, end).map((r: any, i: number) => (
                            <tr key={i} className="border-t">
                                {columns.map((c) => {
                                const key = c.key;
                                let cell: any = "—";
                                if (key === "entity") cell = r.entity ?? r.student ?? "—";
                                else if (key === "day") cell = r.day ?? "—";
                                else if (key === "block") cell = Array.isArray(r.blocks) ? r.blocks.join(", ") : (r.block ?? "—");
                                else if (key === "course") cell = r.course ?? "—";
                                else if (key === "crn") cell = r.crn ?? "—";
                                else if (key === "conflicting_courses") cell = (r.conflicting_courses || []).join ? (r.conflicting_courses || []).join(", ") : String(r.conflicting_courses ?? "—");
                                else if (key === "reason") cell = r.reason ?? "—";
                                else if (key === "size") cell = r.size ?? "—";

                                return (
                                  <td key={key} className="px-2 py-2">{cell}</td>
                                );
                              })}
                            </tr>
                          ))}
                        </tbody>
                      </table>

                      <div className="flex items-center justify-between mt-2">
                        <div className="text-sm text-muted-foreground">
                          Showing {rowsForActive.length === 0 ? 0 : start + 1}-{end} of {rowsForActive.length}
                        </div>
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            disabled={page <= 0}
                            onClick={() => setPage(activeTab, Math.max(0, page - 1))}
                          >
                            Prev
                          </Button>
                          <Button
                            size="sm"
                            disabled={page >= totalPages - 1}
                            onClick={() => setPage(activeTab, Math.min(totalPages - 1, page + 1))}
                          >
                            Next
                          </Button>
                        </div>
                      </div>
                    </>
                  );
                })()}
              </div>
            </CardContent>
          </Card>

          {/* Conflict Definitions: helpful descriptions for each conflict type */}
          <div className="mt-4 bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold mb-3">Conflict Definitions</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
              {Object.keys(conflictTypeMap).map((type) => (
                <div key={type} className="flex flex-col">
                  <div className="font-medium flex items-center gap-2">
                    <span className="inline-flex items-center">{getIconForType(type)}</span>
                    <span>{conflictTypeMap[type] ?? type}</span>
                  </div>
                  <div className="text-muted-foreground text-sm">{conflictDescriptions[type] ?? conflictDescriptions.unknown}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
