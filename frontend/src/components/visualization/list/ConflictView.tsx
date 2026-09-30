// biome-ignore-all lint/suspicious/noExplicitAny: this file require conflict types definitions
import {
  AlertTriangle,
  Briefcase,
  Calendar,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Clock,
  GraduationCap,
  UserX,
} from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  ConflictStat,
  conflictDescriptions,
  conflictTypeMap,
  getIconForType,
} from "@/lib/hooks/useConflictData";
import {
  type ConflictCourse,
  type ConflictRow,
  isPersonConflictType,
  useConflictDataSimple,
} from "@/lib/hooks/useConflictDataSimple";
import type { ConflictMetrics } from "@/lib/types/conflict.types";
import { cn } from "@/lib/utils";

const PAGE_SIZES = [10, 25, 50, 100];
// Rows-per-page lasts for the browser session only.
const PAGE_SIZE_STORAGE_KEY = "conflictView.pageSize";

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

function courseTooltip({ course, crn, exam }: ConflictCourse): string {
  const lines = [[course, crn && `CRN ${crn}`].filter(Boolean).join(" · ")];
  if (exam?.Room) lines.push(`Room: ${exam.Room} (capacity ${exam.Capacity})`);
  if (exam?.Size != null) lines.push(`Enrolled: ${exam.Size}`);
  if (exam?.Instructor) lines.push(`Instructor: ${exam.Instructor}`);
  return lines.join("\n");
}

function CoursePill({ course }: { course: ConflictCourse }) {
  return (
    <Badge
      variant="outline"
      title={courseTooltip(course)}
      className="w-40 justify-between cursor-default border-yellow-200 bg-yellow-50 text-yellow-950"
    >
      <span className="truncate font-semibold">
        {course.course || course.crn}
      </span>
      {course.course && course.crn && (
        <span className="tabular-nums opacity-70">{course.crn}</span>
      )}
    </Badge>
  );
}

function PaginationBar({
  start,
  end,
  total,
  noun,
  page,
  totalPages,
  onPage,
  pageSize,
  onPageSize,
}: {
  start: number;
  end: number;
  total: number;
  noun: string;
  page: number;
  totalPages: number;
  onPage: (p: number) => void;
  pageSize: number;
  /** Omit to hide the rows-per-page picker. */
  onPageSize?: (size: number) => void;
}) {
  const pageButtons = [
    { label: "First page", icon: ChevronsLeft, to: 0 },
    { label: "Previous page", icon: ChevronLeft, to: page - 1 },
    { label: "Next page", icon: ChevronRight, to: page + 1 },
    { label: "Last page", icon: ChevronsRight, to: totalPages - 1 },
  ];
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 py-2">
      <div className="text-sm text-muted-foreground">
        Showing {total === 0 ? 0 : start + 1}-{end} of {total}
        {noun}
      </div>
      <div className="flex items-center gap-2">
        {onPageSize && (
          <>
            <span className="text-sm text-muted-foreground">Rows per page</span>
            <Select
              value={String(pageSize)}
              onValueChange={(v) => onPageSize(Number(v))}
            >
              <SelectTrigger size="sm" aria-label="Rows per page">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PAGE_SIZES.map((n) => (
                  <SelectItem key={n} value={String(n)}>
                    {n}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </>
        )}
        <span className="text-sm text-muted-foreground tabular-nums">
          Page {page + 1} of {totalPages}
        </span>
        {pageButtons.map(({ label, icon: Icon, to }) => (
          <Button
            key={label}
            variant="outline"
            size="icon-sm"
            aria-label={label}
            title={label}
            disabled={to < 0 || to >= totalPages || to === page}
            onClick={() => onPage(to)}
          >
            <Icon />
          </Button>
        ))}
      </div>
    </div>
  );
}

// Paginated table for a conflict tab. Person-based tabs keep one logical row
// per student/instructor: NUId and count span one sub-row per conflict.
// Fixed layout keeps column widths stable across pages.
function ConflictTable({
  rowsForActive,
  activeTabId,
  page,
  setPageForTab,
  pageSize,
  setPageSize,
}: {
  rowsForActive: ConflictRow[];
  activeTabId: string;
  page: number;
  setPageForTab: (tab: string, p: number) => void;
  pageSize: number;
  setPageSize: (size: number) => void;
}) {
  const totalPages = Math.max(1, Math.ceil(rowsForActive.length / pageSize));
  const start = page * pageSize;
  const end = Math.min(rowsForActive.length, start + pageSize);

  const isInstructorConflict =
    activeTabId === "back_to_back_instructor" ||
    activeTabId === "instructor_double_book" ||
    activeTabId === "instructor_gt_max_per_day";
  const isPersonTab = isPersonConflictType(activeTabId);
  const entityLabel = isInstructorConflict ? "Instructor" : "NUId";

  const recordColumns = (
    [
      { key: "entity", label: entityLabel },
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

  // Back-to-back records carry only time slots (no courses): show the slots
  // as pills instead of an always-empty exams column.
  const showCourses = rowsForActive.some(
    (r) => r.kind === "person" && r.instances.some((i) => i.courses.length),
  );

  // Person tabs: percentage widths so columns spread with the table instead
  // of bunching left, while staying independent of page contents. The pills
  // column takes the rest. Record tabs split the width evenly.
  const headers: { label: string; width?: string }[] = isPersonTab
    ? showCourses
      ? [
          { label: entityLabel, width: "w-[15%]" },
          { label: "Conflicts", width: "w-[10%]" },
          { label: "Day", width: "w-[12%]" },
          { label: "Time", width: "w-[15%]" },
          { label: "Conflicting exams" },
        ]
      : [
          { label: entityLabel, width: "w-[18%]" },
          { label: "Conflicts", width: "w-[12%]" },
          { label: "Day", width: "w-[15%]" },
          { label: "Exam times" },
        ]
    : recordColumns.map((c) => ({ label: c.label }));

  const pagination = {
    start,
    end,
    total: rowsForActive.length,
    noun: isPersonTab
      ? isInstructorConflict
        ? " instructors"
        : " students"
      : "",
    page,
    totalPages,
    onPage: (p: number) => setPageForTab(activeTabId, p),
    pageSize,
  };

  return (
    <>
      <PaginationBar {...pagination} onPageSize={setPageSize} />
      <table className="w-full min-w-3xl table-fixed text-sm">
        <thead>
          <tr className="text-left text-muted-foreground">
            {headers.map(({ label, width }) => (
              <th key={label} className={cn("px-2 py-2", width)}>
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rowsForActive.slice(start, end).map((r) => {
            if (r.kind !== "person") {
              return (
                <tr key={r.id} className="border-t align-top">
                  {recordColumns.map((c) => (
                    <td key={c.key} className="px-2 py-2">
                      {r[c.key] || "—"}
                    </td>
                  ))}
                </tr>
              );
            }
            const span = r.instances.length;
            return r.instances.map((inst, i) => (
              <tr
                key={`${r.id}|${inst.day}|${inst.time}`}
                className={cn(
                  "align-top",
                  i === 0
                    ? "border-t"
                    : "border-t border-dashed border-muted-foreground/20",
                )}
              >
                {i === 0 && (
                  <>
                    <td
                      rowSpan={span}
                      className="px-2 py-2 font-medium break-words"
                    >
                      {r.entity || "—"}
                    </td>
                    <td rowSpan={span} className="px-2 py-2">
                      {r.conflictCount}
                    </td>
                  </>
                )}
                <td className="px-2 py-1.5 whitespace-nowrap">
                  {inst.day || "—"}
                </td>
                {showCourses && (
                  <td className="px-2 py-1.5 whitespace-nowrap tabular-nums">
                    {inst.time || "—"}
                  </td>
                )}
                <td className="px-2 py-1.5">
                  <div className="flex flex-wrap gap-1">
                    {showCourses
                      ? inst.courses.map((c) => (
                          <CoursePill key={c.crn || c.course} course={c} />
                        ))
                      : inst.slots.map((slot) => (
                          <Badge
                            key={slot}
                            variant="secondary"
                            className="w-32 tabular-nums"
                          >
                            {slot}
                          </Badge>
                        ))}
                    {showCourses && inst.courses.length === 0 && "—"}
                  </div>
                </td>
              </tr>
            ));
          })}
        </tbody>
      </table>

      <PaginationBar {...pagination} />
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

  const [pageSize, setPageSizeState] = useState(() => {
    const stored =
      typeof window === "undefined"
        ? Number.NaN
        : Number(sessionStorage.getItem(PAGE_SIZE_STORAGE_KEY));
    return PAGE_SIZES.includes(stored) ? stored : PAGE_SIZES[0];
  });

  function setPageSize(size: number) {
    sessionStorage.setItem(PAGE_SIZE_STORAGE_KEY, String(size));
    setPageSizeState(size);
    // Old page indexes are meaningless at the new size.
    setPageByTab({});
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
                  pageSize={pageSize}
                  setPageSize={setPageSize}
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
