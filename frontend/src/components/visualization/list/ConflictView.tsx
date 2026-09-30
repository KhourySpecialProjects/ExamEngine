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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  ConflictStat,
  conflictDescriptions,
  conflictTypeMap,
  getIconForType,
} from "@/lib/hooks/useConflictData";
import {
  type ConflictCourse,
  type ConflictRow,
  type ConflictType,
  isInstructorConflictType,
  isPersonConflictType,
  type RecordConflictRow,
  useConflictDataSimple,
} from "@/lib/hooks/useConflictDataSimple";
import {
  CONFLICT_PAGE_SIZES,
  useConflictViewStore,
} from "@/lib/store/conflictViewStore";
import type { ConflictMetrics } from "@/lib/types/conflict.types";
import { cn } from "@/lib/utils";

type RecordColumnKey = keyof Pick<
  RecordConflictRow,
  "entity" | "day" | "block" | "course" | "crn" | "size"
>;

// Record-row columns a conflict type never shows, even when the data has them.
const HIDDEN_RECORD_COLUMNS: Partial<Record<ConflictType, RecordColumnKey[]>> =
  {
    large_course_not_early: ["block"],
  };

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
  page,
  pageSize,
  total,
  noun,
  onPage,
  onPageSize,
}: {
  page: number;
  pageSize: number;
  total: number;
  /** Pluralized, with a leading space (" students"), or "". */
  noun: string;
  onPage: (p: number) => void;
  /** Omit to hide the rows-per-page picker. */
  onPageSize?: (size: number) => void;
}) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const start = page * pageSize;
  const end = Math.min(total, start + pageSize);
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
                {CONFLICT_PAGE_SIZES.map((n) => (
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
  onPage,
  pageSize,
  onPageSize,
}: {
  rowsForActive: ConflictRow[];
  activeTabId: ConflictType;
  page: number;
  onPage: (p: number) => void;
  pageSize: number;
  onPageSize: (size: number) => void;
}) {
  const isPersonTab = isPersonConflictType(activeTabId);
  const isInstructorTab = isInstructorConflictType(activeTabId);
  const entityLabel = isInstructorTab ? "Instructor" : "NUId";
  const hiddenColumns = HIDDEN_RECORD_COLUMNS[activeTabId] ?? [];

  const recordColumns = (
    [
      { key: "entity", label: entityLabel },
      { key: "day", label: "Day" },
      { key: "block", label: "Block" },
      { key: "course", label: "Course" },
      { key: "crn", label: "CRN" },
      { key: "size", label: "Size" },
    ] satisfies { key: RecordColumnKey; label: string }[]
  ).filter(
    (c) =>
      !hiddenColumns.includes(c.key) &&
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
    page,
    pageSize,
    total: rowsForActive.length,
    noun: isPersonTab ? (isInstructorTab ? " instructors" : " students") : "",
    onPage,
  };
  const start = page * pageSize;

  return (
    <>
      <PaginationBar {...pagination} onPageSize={onPageSize} />
      <Table className="min-w-3xl table-fixed">
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            {headers.map(({ label, width }) => (
              <TableHead
                key={label}
                className={cn("text-muted-foreground", width)}
              >
                {label}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rowsForActive.slice(start, start + pageSize).map((r) => {
            if (r.kind !== "person") {
              return (
                <TableRow key={r.id} className="align-top">
                  {recordColumns.map((c) => (
                    <TableCell key={c.key}>{r[c.key] || "—"}</TableCell>
                  ))}
                </TableRow>
              );
            }
            const span = r.instances.length;
            // Hover highlighting is off: it would light up one sub-row of a
            // person but not the cells spanning the whole group.
            return r.instances.map((inst, i) => (
              <TableRow
                key={`${r.id}|${inst.day}|${inst.time}`}
                className={cn(
                  "align-top hover:bg-transparent",
                  i < span - 1 && "border-dashed border-muted-foreground/20",
                )}
              >
                {i === 0 && (
                  <>
                    <TableCell
                      rowSpan={span}
                      className="align-top font-medium whitespace-normal break-words"
                    >
                      {r.entity || "—"}
                    </TableCell>
                    <TableCell rowSpan={span} className="align-top">
                      {r.conflictCount}
                    </TableCell>
                  </>
                )}
                <TableCell className="align-top">{inst.day || "—"}</TableCell>
                {showCourses && (
                  <TableCell className="align-top tabular-nums">
                    {inst.time || "—"}
                  </TableCell>
                )}
                <TableCell className="align-top whitespace-normal">
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
                </TableCell>
              </TableRow>
            ));
          })}
        </TableBody>
      </Table>
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

  const pageSize = useConflictViewStore((s) => s.pageSize);
  const setPageSize = useConflictViewStore((s) => s.setPageSize);

  const [activeTab, setActiveTab] = useState<string>(
    effectiveTabs[0]?.id ?? "back_to_back",
  );

  const rowsForActive = rowsByType[activeTab] ?? [];
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
              <ConflictTable
                rowsForActive={rowsForActive}
                activeTabId={activeTab}
                page={page}
                onPage={(p) => setPage(activeTab, p)}
                pageSize={pageSize}
                onPageSize={(size) => {
                  setPageSize(size);
                  // Old page indexes are meaningless at the new size.
                  setPageByTab({});
                }}
              />
            </CardContent>
          </Card>

          <ConflictDefinitions />
        </div>
      </div>
    </section>
  );
}
