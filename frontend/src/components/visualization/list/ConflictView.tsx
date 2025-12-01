// "use client";

// biome-ignore-all lint/suspicious/noExplicitAny: this file require conflict types definitions
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  ConflictStat,
  conflictDescriptions,
  conflictTypeMap,
  getIconForType,
  PAGE_SIZE,
} from "@/lib/hooks/useConflictData";
import { useConflictDataSimple } from "@/lib/hooks/useConflictDataSimple";
import type { ConflictMetrics } from "@/lib/types/conflict.types";

// Legend: conflict type definitions
function ConflictDefinitions() {
  return (
    <div className="mt-4 bg-white rounded-lg shadow p-4">
      <h3 className="font-semibold mb-3">Conflict Definitions</h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
        {Object.keys(conflictTypeMap).map((type) => (
          <div key={type} className="flex flex-col">
            <div className="font-medium flex items-center gap-2">
              <span className="inline-flex items-center">
                {getIconForType(type)}
              </span>
              <span>{conflictTypeMap[type] ?? type}</span>
            </div>
            <div className="text-muted-foreground text-sm">
              {conflictDescriptions[type] ?? conflictDescriptions.unknown}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Paginated table for a conflict tab
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
    entity: rowsForActive.some(
      (r: any) => r.entity != null && String(r.entity).trim() !== "",
    ),
    day: rowsForActive.some(
      (r: any) => r.day != null && String(r.day).trim() !== "",
    ),
    block: rowsForActive.some((r: any) =>
      Array.isArray(r.blocks)
        ? r.blocks.length > 0
        : r.block != null && String(r.block).trim() !== "",
    ),
    course: rowsForActive.some(
      (r: any) => r.course != null && String(r.course).trim() !== "",
    ),
    crn: rowsForActive.some(
      (r: any) => r.crn != null && String(r.crn).trim() !== "",
    ),
    conflicting_courses: rowsForActive.some((r: any) =>
      Array.isArray(r.conflicting_courses)
        ? r.conflicting_courses.length > 0
        : r.conflicting_courses != null &&
          String(r.conflicting_courses).trim() !== "",
    ),
    size: rowsForActive.some(
      (r: any) => r.size != null && String(r.size).trim() !== "",
    ),
  };

  // Helper function to format block display with times
  const formatBlockDisplay = (row: any): string => {
    // For back-to-back conflicts, show times if available
    if (Array.isArray(row.blocks) && row.blocks.length > 0) {
      if (Array.isArray(row.block_times) && row.block_times.length > 0) {
        // Show times for each block: "Time1, Time2"
        return row.block_times.join(", ");
      }
      // Fallback: show block numbers if times not available
      return row.blocks.join(", ");
    }
    // For single block conflicts, show block_time if available
    if (row.block_time) {
      return row.block_time;
    }
    // Fallback: show block number
    return row.block?.toString() || "—";
  };

  if (activeTabId === "large_course_not_early") {
    has.block = false;
    has.conflicting_courses = false;
  }

  const columns: Array<{ key: string; label: string }> = [];
  if (has.entity) columns.push({ key: "entity", label: "Entity" });
  if (has.day) columns.push({ key: "day", label: "Day" });
  if (has.block) {
    // For back-to-back conflicts, change label to show it's times
    const isBackToBack =
      activeTabId === "back_to_back" ||
      activeTabId === "back_to_back_student" ||
      activeTabId === "back_to_back_instructor";
    columns.push({ key: "block", label: isBackToBack ? "Time" : "Block" });
  }
  if (has.course) columns.push({ key: "course", label: "Course" });
  if (has.crn) columns.push({ key: "crn", label: "CRN" });
  if (has.size) columns.push({ key: "size", label: "Size" });
  if (has.conflicting_courses)
    columns.push({
      key: "conflicting_courses",
      label: "Conflicting Courses",
    });

  return (
    <>
      <table className="w-full table-auto text-sm">
        <thead>
          <tr className="text-left text-muted-foreground">
            {columns.map((c) => (
              <th key={c.key} className="px-2 py-2">
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rowsForActive.slice(start, end).map((r: any, i: number) => (
            // biome-ignore lint/suspicious/noArrayIndexKey: temporary key usage
            <tr key={i} className="border-t">
              {columns.map((c) => {
                const key = c.key;
                let cell: any = "—";
                if (key === "entity") {
                  // For instructor conflicts, prefer instructor_name if available
                  const isInstructorConflict =
                    activeTabId === "back_to_back_instructor" ||
                    activeTabId === "instructor_double_book" ||
                    activeTabId === "instructor_gt_max_per_day";
                  if (isInstructorConflict && r.instructor_name) {
                    cell = r.instructor_name;
                  } else {
                    cell = r.entity ?? r.student ?? r.instructor_name ?? "—";
                  }
                } else if (key === "day") cell = r.day ?? "—";
                else if (key === "block") {
                  // Use the helper function to format block display with times
                  cell = formatBlockDisplay(r);
                } else if (key === "course") cell = r.course ?? "—";
                else if (key === "crn") cell = r.crn ?? "—";
                else if (key === "conflicting_courses")
                  cell = (r.conflicting_courses || []).join
                    ? (r.conflicting_courses || []).join(", ")
                    : String(r.conflicting_courses ?? "—");
                else if (key === "size") cell = r.size ?? "—";

                return (
                  <td key={key} className="px-2 py-2">
                    {cell}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>

      <div className="flex items-center justify-between mt-2">
        <div className="text-sm text-muted-foreground">
          Showing {rowsForActive.length === 0 ? 0 : start + 1}-{end} of{" "}
          {rowsForActive.length}
        </div>
        <div className="flex gap-2">
          <Button
            size="sm"
            disabled={page <= 0}
            onClick={() => setPageForTab(activeTabId, Math.max(0, page - 1))}
          >
            Prev
          </Button>
          <Button
            size="sm"
            disabled={page >= totalPages - 1}
            onClick={() =>
              setPageForTab(activeTabId, Math.min(totalPages - 1, page + 1))
            }
          >
            Next
          </Button>
        </div>
      </div>
    </>
  );
}

// Conflict View: show backend-provided metrics and rows
export default function ConflictView({
  metrics,
}: {
  metrics?: Partial<ConflictMetrics>;
}) {
  // Use the simple backend-driven conflict hook — backend returns a single normalized shape
  const {
    metrics: backendMetrics,
    rowsByType,
    types,
  } = useConflictDataSimple();
  const conflictTypeRows: Record<string, any[]> = { ...(rowsByType || {}) };

  // Prefer backend-provided metrics when available
  const finalMerged = {
    hard_student_conflicts: backendMetrics?.hard_student_conflicts ?? 0,
    hard_instructor_conflicts: backendMetrics?.hard_instructor_conflicts ?? 0,
    students_back_to_back: backendMetrics?.students_back_to_back ?? 0,
    instructors_back_to_back: backendMetrics?.instructors_back_to_back ?? 0,
    large_courses_not_early: backendMetrics?.large_courses_not_early ?? 0,
    student_gt3_per_day: backendMetrics?.student_gt3_per_day ?? 0,
  };

  const dynamicTabEntries =
    types && types.length > 0
      ? types.map((t) => ({ id: t, label: conflictTypeMap[t] ?? t }))
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

  const [activeTab, setActiveTab] = useState<string>(
    effectiveTabs[0]?.id ?? "back_to_back",
  );

  const summaryCards = [
    {
      label: "Student Double-Book",
      value: finalMerged.hard_student_conflicts,
      variant: "destructive",
    },
    {
      label: "Instructor Double-Book",
      value: finalMerged.hard_instructor_conflicts,
      variant: "destructive",
    },
    {
      label: "Student >3/day",
      value: finalMerged.student_gt3_per_day,
      variant: "destructive",
    },
    {
      label: "Students Back-to-Back",
      value: finalMerged.students_back_to_back,
      badgeClassName: "bg-amber-600 text-white",
    },
    {
      label: "Instructors Back-to-Back",
      value: finalMerged.instructors_back_to_back,
      badgeClassName: "bg-amber-600 text-white",
    },
    {
      label: "Large Course Not Early",
      value: finalMerged.large_courses_not_early,
      badgeClassName: "bg-amber-600 text-white",
    },
  ];

  const rowsForActive = conflictTypeRows[activeTab] ?? [];
  const page = getPage(activeTab);

  return (
    <section className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">Conflict View</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Quick overview of schedule conflicts
        </p>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-6">
        {summaryCards.map((c) => (
          <ConflictStat
            key={c.label}
            label={c.label}
            value={c.value}
            variant={(c as any).variant}
            badgeClassName={(c as any).badgeClassName}
          />
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
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <span className="inline-flex items-center">
                  {getIconForType(activeTab)}
                </span>
                <span>
                  {effectiveTabs.find((x) => x.id === activeTab)?.label ??
                    "Conflicts"}
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-auto">
                <ConflictTable
                  rowsForActive={rowsForActive}
                  activeTabId={activeTab}
                  page={page}
                  setPageForTab={setPage}
                />
              </div>
            </CardContent>
          </Card>

          <ConflictDefinitions />
        </div>
      </div>
    </section>
  );
}
