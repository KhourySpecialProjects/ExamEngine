// "use client";

// header icon removed
import { useState } from "react";
import { User, Users, Clock, Calendar, AlertTriangle, BookOpen } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useExamTable } from "@/lib/hooks/useExamTable";
import { useScheduleData } from "@/lib/hooks/useScheduleData";
import { useScheduleStore } from "@/lib/store/scheduleStore";
import { mapConflictsToRows } from "@/lib/utils";
import { ConflictMetrics } from "@/lib/types/conflict.types";
import {
  computeAggregatesFromExams,
  computeTotalsFromBreakdown,
  PAGE_SIZE,
  conflictTypeMap,
  conflictDescriptions,
  dayNameMap,
  getIconForType,
  ConflictStat,
} from "@/lib/hooks/useConflictData"


/**
 * Main Conflict View component.
 * Displays summary metrics and a tabbed listing of conflict rows.
 * It combines computed aggregates from local exams with backend breakdowns,
 * preferring backend totals when available.
 */
export default function ConflictView({
  metrics,
}: {
  metrics?: Partial<ConflictMetrics>;
}) {
  const { allExams } = useExamTable();
  const { calendarRows } = useScheduleData();
  const derived = computeAggregatesFromExams(allExams ?? []);
  const currentSchedule = useScheduleStore((s) => s.currentSchedule);
  const breakdown = currentSchedule?.conflicts?.breakdown ?? [];

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

  // Use backend-mapped rows only; do not synthesize fake rows from local data.
  const mappedRows = mapConflictsToRows(allExams ?? [], breakdown ?? []);
  const displayBackRows = (mappedRows.backRows && mappedRows.backRows.length > 0) ? mappedRows.backRows : [];
  const displayLargeRows = (mappedRows.largeRows && mappedRows.largeRows.length > 0) ? mappedRows.largeRows : [];


  const conflictTypeRows: Record<string, any[]> = {};


  /**
   * Find an exam object in `allExams` by matching common CRN-like fields.
   * Returns null when no matching exam is found.
   */
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

    const sizeVal = exam?.enrollment ?? exam?.size ?? exam?.students_count ?? null;

    const entityVal = conf.student_id ? `S:${conf.student_id}` : conf.instructor_id ? `I:${conf.instructor_id}` : conf.entity_id ?? null;

    let blockVal: string | null = null;
    if (Array.isArray(conf.blocks)) {
      blockVal = conf.blocks.join(", ");
    } else if (conf.block_time) {
      blockVal = conf.block_time;
    } else if (conf.block !== undefined && conf.block !== null) {
      const bStr = String(conf.block);
      const match = (calendarRows || []).find((r: any) => {
        const ts = String(r.timeSlot || "");
        return ts.split(" ")[0] === bStr;
      });
      blockVal = match ? String(match.timeSlot) : String(conf.block);
    }

    let conflictingCourses: string[] = [];
    if (Array.isArray(conf.conflicting_courses)) conflictingCourses = conf.conflicting_courses.map((c: any) => String(c));
    else if (Array.isArray(conf.conflicting_crns)) conflictingCourses = conf.conflicting_crns.map((c: any) => String(c));
    else if (typeof conf.conflicting_courses === "string") conflictingCourses = [conf.conflicting_courses];

    const row = {
      entity: entityVal,
      type,
      day: dayNameMap[conf.day] ?? conf.day ?? conf.block_day ?? null,
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

    // --- derive reliable counts from mapped rows / conflictTypeRows ---
    // Prefer explicit breakdown counts when present, otherwise count table rows.
    const studentDoubleCount = (conflictTypeRows["student_double_book"]?.length ?? 0) || (mappedRows.backRows?.filter(Boolean).length ? 0 : 0);
    const instructorDoubleCount = (conflictTypeRows["instructor_double_book"]?.length ?? 0) || 0;

    // Back-to-back: count explicit student/instructor types, plus inspect generic 'back_to_back' rows
    let studentsBackToBackCount = conflictTypeRows["back_to_back_student"]?.length ?? 0;
    let instructorsBackToBackCount = conflictTypeRows["back_to_back_instructor"]?.length ?? 0;
    const genericBack = conflictTypeRows["back_to_back"] ?? [];
    for (const r of genericBack) {
      const ent = r?.entity ?? "";
      if (typeof ent === "string" && ent.startsWith("I:")) instructorsBackToBackCount += 1;
      else studentsBackToBackCount += 1;
    }

    const largeCoursesNotEarlyCount = (conflictTypeRows["large_course_not_early"]?.length ?? 0) || (displayLargeRows?.length ?? 0);

    const finalMerged: ConflictMetrics = {
      hard_student_conflicts:
        metrics?.hard_student_conflicts ?? (mappedTotals.hard_student_conflicts > 0 ? mappedTotals.hard_student_conflicts : derived.hard_student_conflicts),
      hard_instructor_conflicts:
        metrics?.hard_instructor_conflicts ?? (mappedTotals.hard_instructor_conflicts > 0 ? mappedTotals.hard_instructor_conflicts : derived.hard_instructor_conflicts),
      students_back_to_back:
        metrics?.students_back_to_back ?? (mappedTotals.students_back_to_back > 0 ? mappedTotals.students_back_to_back : studentsBackToBackCount ?? derived.students_back_to_back),
      instructors_back_to_back:
        metrics?.instructors_back_to_back ?? (mappedTotals.instructors_back_to_back > 0 ? mappedTotals.instructors_back_to_back : instructorsBackToBackCount ?? derived.instructors_back_to_back),
      large_courses_not_early:
        metrics?.large_courses_not_early ?? (mappedTotals.large_courses_not_early > 0 ? mappedTotals.large_courses_not_early : largeCoursesNotEarlyCount ?? derived.large_courses_not_early),
      student_gt3_per_day:
        metrics?.student_gt3_per_day ?? (mappedTotals.student_gt3_per_day > 0 ? mappedTotals.student_gt3_per_day : derived.student_gt3_per_day),
    };

  const dynamicTabEntries = Object.keys(conflictTypeRows).length > 0
    ? Object.keys(conflictTypeRows).map((t) => ({ id: t, label: conflictTypeMap[t] ?? t }))
    : [
        { id: "back_to_back", label: "Back-to-Back" },
        { id: "large_course_not_early", label: "Large courses not early" },
      ];

  const effectiveTabs = dynamicTabEntries;

  const [pageByTab, setPageByTab] = useState<Record<string, number>>({});

  function setPage(tabId: string, page: number) {
    setPageByTab((s) => ({ ...s, [tabId]: page }));
  }

  function getPage(tabId: string) {
    return pageByTab[tabId] ?? 0;
  }

  const [activeTab, setActiveTab] = useState<string>(effectiveTabs[0]?.id ?? "back_to_back");

  /**
   * Render a generic, paginated table for a given conflict-type tab.
   * - `rowsForActive` is the array of rows to display
   * - `activeTabId` controls special column rules (e.g. large courses)
   */
  function ConflictTable({
    rowsForActive,
    activeTabId,
    page,
    setPageForTab,
  }: {
    rowsForActive: any[];
    activeTabId: string;
    page: number;
    setPageForTab: (tab: string, p: number) => void;
  }) {
    const totalPages = Math.max(1, Math.ceil(rowsForActive.length / PAGE_SIZE));
    const start = page * PAGE_SIZE;
    const end = Math.min(rowsForActive.length, start + PAGE_SIZE);

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

    if (activeTabId === "large_course_not_early") {
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
            <Button size="sm" disabled={page <= 0} onClick={() => setPageForTab(activeTabId, Math.max(0, page - 1))}>Prev</Button>
            <Button size="sm" disabled={page >= totalPages - 1} onClick={() => setPageForTab(activeTabId, Math.min(totalPages - 1, page + 1))}>Next</Button>
          </div>
        </div>
      </>
    );
  }

  /**
   * Render the conflict type definitions panel used as a legend/help.
   */
  function ConflictDefinitions() {
    return (
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
    );
  }

  const summaryCards = [
    { label: "Student Double-Book", value: finalMerged.hard_student_conflicts, variant: "destructive" },
    { label: "Instructor Double-Book", value: finalMerged.hard_instructor_conflicts, variant: "destructive" },
    { label: "Student >3/day", value: finalMerged.student_gt3_per_day, variant: "destructive" },
    { label: "Students Back-to-Back", value: finalMerged.students_back_to_back, badgeClassName: "bg-amber-600 text-white" },
    { label: "Instructors Back-to-Back", value: finalMerged.instructors_back_to_back, badgeClassName: "bg-amber-600 text-white" },
    { label: "Large Course Not Early", value: finalMerged.large_courses_not_early, badgeClassName: "bg-amber-600 text-white" },
  ];

  const rowsForActive = conflictTypeRows[activeTab] ?? (activeTab === "back_to_back" ? displayBackRows : activeTab === "large_course_not_early" ? displayLargeRows : []);
  const page = getPage(activeTab);

  return (
    <section className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">Conflict View</h1>
        <p className="text-sm text-muted-foreground mt-1">Quick overview of schedule conflicts</p>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-6">
        {summaryCards.map((c) => (
          <ConflictStat key={c.label} label={c.label} value={c.value} variant={(c as any).variant} badgeClassName={(c as any).badgeClassName} />
        ))}
      </div>

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
                activeTab === t.id ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground hover:bg-muted/80"
              }`}
            >
              {t.label}
            </Button>
          ))}
        </div>

        <div className="mt-3">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <span className="inline-flex items-center">{getIconForType(activeTab)}</span>
                <span>{effectiveTabs.find((x) => x.id === activeTab)?.label ?? "Conflicts"}</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-auto">
                <ConflictTable rowsForActive={rowsForActive} activeTabId={activeTab} page={page} setPageForTab={setPage} />
              </div>
            </CardContent>
          </Card>

          <ConflictDefinitions />
        </div>
      </div>
    </section>
  );
}