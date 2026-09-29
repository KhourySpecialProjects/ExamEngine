// biome-ignore-all lint/suspicious/noExplicitAny: this file require conflict types definitions
import {
  AlertTriangle,
  Briefcase,
  Calendar,
  Clock,
  GraduationCap,
  UserX,
} from "lucide-react";
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
import {
  type ConflictRow,
  isPersonConflictType,
  useConflictDataSimple,
} from "@/lib/hooks/useConflictDataSimple";
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

// Paginated table for a conflict tab. Person-based tabs have one row per
// student/instructor listing all of their conflicting exams.
function ConflictTable({
  rowsForActive,
  activeTabId,
  page,
  setPageForTab,
}: {
  rowsForActive: ConflictRow[];
  activeTabId: string;
  page: number;
  setPageForTab: (tab: string, p: number) => void;
}) {
  const totalPages = Math.max(1, Math.ceil(rowsForActive.length / PAGE_SIZE));
  const start = page * PAGE_SIZE;
  const end = Math.min(rowsForActive.length, start + PAGE_SIZE);

  const isInstructorConflict =
    activeTabId === "back_to_back_instructor" ||
    activeTabId === "instructor_double_book" ||
    activeTabId === "instructor_gt_max_per_day";
  const isPersonTab = isPersonConflictType(activeTabId);

  const recordColumns = (
    [
      { key: "entity", label: isInstructorConflict ? "Instructor" : "NUId" },
      { key: "day", label: "Day" },
      { key: "block", label: "Block" },
      { key: "course", label: "Course" },
      { key: "crn", label: "CRN" },
      { key: "size", label: "Size" },
    ] as const
  ).filter(
    (c) =>
      !(activeTabId === "large_course_not_early" && c.key === "block") &&
      rowsForActive.some(
        (r) =>
          r.kind === "record" &&
          r[c.key] != null &&
          String(r[c.key]).trim() !== "",
      ),
  );

  const headers = isPersonTab
    ? [
        isInstructorConflict ? "Instructor" : "NUId",
        "Conflicts",
        "Conflicting exams",
      ]
    : recordColumns.map((c) => c.label);

  return (
    <>
      <table className="w-full table-auto text-sm">
        <thead>
          <tr className="text-left text-muted-foreground">
            {headers.map((label) => (
              <th key={label} className="px-2 py-2">
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rowsForActive.slice(start, end).map((r) => (
            <tr key={r.id} className="border-t align-top">
              {r.kind === "person" ? (
                <>
                  <td className="px-2 py-2">{r.entity || "—"}</td>
                  <td className="px-2 py-2">{r.conflictCount}</td>
                  <td className="px-2 py-2">
                    <ul className="space-y-0.5">
                      {r.instances.map((inst) => {
                        const when = [inst.day, inst.time]
                          .filter(Boolean)
                          .join(" ");
                        const exams = inst.courses
                          .map((c) =>
                            c.course && c.crn
                              ? `${c.course} (${c.crn})`
                              : c.course || c.crn,
                          )
                          .join(", ");
                        return (
                          <li key={`${inst.day}|${inst.time}`}>
                            {exams ? `${when || "—"}: ${exams}` : when || "—"}
                          </li>
                        );
                      })}
                    </ul>
                  </td>
                </>
              ) : (
                recordColumns.map((c) => (
                  <td key={c.key} className="px-2 py-2">
                    {r[c.key] || "—"}
                  </td>
                ))
              )}
            </tr>
          ))}
        </tbody>
      </table>

      <div className="flex items-center justify-between mt-2">
        <div className="text-sm text-muted-foreground">
          Showing {rowsForActive.length === 0 ? 0 : start + 1}-{end} of{" "}
          {rowsForActive.length}
          {isPersonTab && (isInstructorConflict ? " instructors" : " students")}
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
  const conflictTypeRows: Record<string, ConflictRow[]> = {
    ...(rowsByType || {}),
  };

  // Prefer backend-provided metrics when available
  const finalMerged = {
    hard_student_conflicts: backendMetrics?.hard_student_conflicts ?? 0,
    hard_instructor_conflicts: backendMetrics?.hard_instructor_conflicts ?? 0,
    students_back_to_back: backendMetrics?.students_back_to_back ?? 0,
    instructors_back_to_back: backendMetrics?.instructors_back_to_back ?? 0,
    large_courses_not_early: backendMetrics?.large_courses_not_early ?? 0,
    student_gt3_per_day: backendMetrics?.student_gt3_per_day ?? 0,
  };

  const summaryCards = [
    {
      label: "Student Conflicts",
      value: finalMerged.hard_student_conflicts,
      subtitle: "Students with overlapping exams",
      icon: <UserX className="h-4 w-4" />,
      variant:
        finalMerged.hard_student_conflicts > 0 ? "destructive" : "success",
    },
    {
      label: "Instructor Conflicts",
      value: finalMerged.hard_instructor_conflicts,
      subtitle: "Instructors with overlapping exams",
      icon: <Briefcase className="h-4 w-4" />,
      variant:
        finalMerged.hard_instructor_conflicts > 0 ? "destructive" : "success",
    },
    {
      label: "Overloaded Students",
      value: finalMerged.student_gt3_per_day,
      subtitle: "Students with 3+ exams in one day",
      icon: <Calendar className="h-4 w-4" />,
      variant: finalMerged.student_gt3_per_day > 0 ? "destructive" : "success",
    },
    {
      label: "Student Back-to-Back",
      value: finalMerged.students_back_to_back,
      subtitle: "Students with back-to-back exams",
      icon: <Clock className="h-4 w-4" />,
      variant: finalMerged.students_back_to_back > 0 ? "warning" : "success",
    },
    {
      label: "Instructor Back-to-Back",
      value: finalMerged.instructors_back_to_back,
      subtitle: "Instructors with back-to-back exams",
      icon: <GraduationCap className="h-4 w-4" />,
      variant: finalMerged.instructors_back_to_back > 0 ? "warning" : "success",
    },
    {
      label: "Late Large Courses",
      value: finalMerged.large_courses_not_early,
      subtitle: "100+ enrollment scheduled late",
      icon: <AlertTriangle className="h-4 w-4" />,
      variant: finalMerged.large_courses_not_early > 0 ? "warning" : "success",
    },
  ] as const;

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

  const rowsForActive = conflictTypeRows[activeTab] ?? [];
  const page = getPage(activeTab);

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <div className="pl-2">
          <h1 className="text-2xl font-bold">Conflict View</h1>
          <p className="text-muted-foreground">
            Quick overview of schedule conflicts
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-6">
        {summaryCards.map((c) => (
          <ConflictStat
            key={c.label}
            label={c.label}
            value={c.value}
            icon={c.icon}
            subtitle={c.subtitle}
            variant={c.variant}
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
