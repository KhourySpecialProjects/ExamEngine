// biome-ignore-all lint/suspicious/noExplicitAny: this file require conflict types definitions
import {
  AlertTriangle,
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  Briefcase,
  Calendar,
  CalendarX,
  Clock,
  GraduationCap,
  SquareArrowOutUpRight,
  UserX,
} from "lucide-react";
import { useState } from "react";
import { CopyButton } from "@/components/common/CopyButton";
import { PaginationBar } from "@/components/common/table/PaginationBar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ButtonGroup } from "@/components/ui/button-group";
import {
  Card,
  CardAction,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { ConflictMetric } from "@/lib/api/schedules";
import {
  CONFLICT_TYPE_ORDER,
  ConflictStat,
  conflictDescriptions,
  conflictTypeMap,
  conflictTypeRank,
  getIconForType,
} from "@/lib/hooks/useConflictData";
import {
  type ConflictCourse,
  type ConflictRow,
  type ConflictType,
  type CourseSortColumn,
  isBackToBackConflictType,
  isInstructorConflictType,
  isPerDayLimitConflictType,
  isPersonConflictType,
  type PersonConflictRow,
  type PersonSortColumn,
  type RecordConflictRow,
  type RecordSortColumn,
  type SortState,
  sortCourseSummaries,
  sortPersonRows,
  sortRecordRows,
  summarizeConflictsByCourse,
  useConflictDataSimple,
} from "@/lib/hooks/useConflictDataSimple";
import { useConflictViewStore } from "@/lib/store/conflictViewStore";
import { useSchedulesStore } from "@/lib/store/schedulesStore";
import { cn } from "@/lib/utils";
import { CourseConflictDialog } from "./CourseConflictDialog";

// Record-row columns a conflict type never shows, even when the data has them.
const HIDDEN_RECORD_COLUMNS: Partial<Record<ConflictType, RecordSortColumn[]>> =
  {
    large_course_not_early: ["block"],
  };

// Legend: conflict type definitions
function ConflictDefinitions() {
  return (
    <div className="mt-4 bg-white rounded-lg shadow p-4">
      <h3 className="font-semibold mb-3">Conflict Definitions</h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
        {CONFLICT_TYPE_ORDER.map((type) => (
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

// Fixed width so pills line up in columns across rows.
function CoursePill({
  course,
  onOpen,
}: {
  course: ConflictCourse;
  onOpen: (course: ConflictCourse) => void;
}) {
  const name = course.course || `CRN ${course.crn}`;
  return (
    <Badge
      variant="outline"
      title={courseTooltip(course)}
      className="w-52 gap-0.5 py-0 pr-1 pl-0 border-yellow-200 bg-yellow-50 text-yellow-950"
    >
      <button
        type="button"
        aria-label={`Show conflicts for ${name}`}
        onClick={() => onOpen(course)}
        className="flex min-w-0 flex-1 items-center justify-between gap-1 rounded-sm py-0.5 pl-2 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
      >
        <span className="truncate font-semibold">
          {course.course || course.crn}
        </span>
        {course.course && course.crn && (
          <span className="tabular-nums opacity-70">{course.crn}</span>
        )}
      </button>
      {course.crn && (
        <CopyButton value={course.crn} label={`Copy CRN ${course.crn}`} />
      )}
      <button
        type="button"
        aria-label={`Open conflict details for ${name}`}
        title={`Open conflict details for ${name}`}
        onClick={() => onOpen(course)}
        className="inline-flex shrink-0 items-center justify-center rounded-sm p-0.5 opacity-60 hover:opacity-100 focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <SquareArrowOutUpRight className="size-3" aria-hidden />
      </button>
    </Badge>
  );
}

/** Person-tab header ids → sort key; Day and Time both sort by earliest conflict. */
const PERSON_SORT_COLUMNS: Record<string, PersonSortColumn> = {
  entity: "entity",
  conflictCount: "conflictCount",
  day: "earliest",
  time: "earliest",
};

/** The per-course view opens sorted by who is affected, most first. */
const DEFAULT_COURSE_SORT: SortState<CourseSortColumn> = {
  column: "people",
  direction: "desc",
};

interface TableColumn {
  /** Sort id; omit for an unsortable column. */
  id?: string;
  label: string;
  width?: string;
}

function ConflictTableHead({
  column,
  sort,
  onSort,
}: {
  column: TableColumn;
  sort?: SortState<string>;
  onSort: (column: string) => void;
}) {
  const { id, label, width } = column;
  const direction = id && sort?.column === id ? sort.direction : undefined;
  const Icon =
    direction === "asc"
      ? ArrowUp
      : direction === "desc"
        ? ArrowDown
        : ArrowUpDown;
  return (
    <TableHead
      className={cn("text-muted-foreground", width)}
      aria-sort={
        direction === "asc"
          ? "ascending"
          : direction === "desc"
            ? "descending"
            : undefined
      }
    >
      {id ? (
        <Button
          variant="ghost"
          size="sm"
          className="-ml-3 text-muted-foreground"
          onClick={() => onSort(id)}
        >
          {label}
          <Icon className={cn("size-3.5", !direction && "opacity-50")} />
        </Button>
      ) : (
        label
      )}
    </TableHead>
  );
}

// Paginated, sortable table for a conflict tab. Person-based tabs keep one
// logical row per student/instructor: NUId and count span one sub-row per
// conflict, and sorting/paging act on people. `byCourse` shows one row per
// course instead. Fixed layout keeps column widths stable across pages.
function ConflictTable({
  rowsForActive,
  activeTabId,
  byCourse,
  sort,
  onSort,
  page,
  onPage,
  pageSize,
  onPageSize,
  onOpenCourse,
}: {
  rowsForActive: ConflictRow[];
  activeTabId: ConflictType;
  byCourse: boolean;
  sort?: SortState<string>;
  onSort: (column: string) => void;
  page: number;
  onPage: (p: number) => void;
  pageSize: number;
  onPageSize: (size: number) => void;
  onOpenCourse: (course: ConflictCourse) => void;
}) {
  const isPersonTab = isPersonConflictType(activeTabId);
  const isInstructorTab = isInstructorConflictType(activeTabId);
  const entityLabel = isInstructorTab ? "Instructor" : "NUId";
  const peopleNoun = isInstructorTab ? " instructors" : " students";
  const start = page * pageSize;
  const pagination = { page, pageSize, onPage };

  const header = (columns: TableColumn[]) => (
    <TableHeader>
      <TableRow className="hover:bg-transparent">
        {columns.map((c) => (
          <ConflictTableHead
            key={c.label}
            column={c}
            sort={sort}
            onSort={onSort}
          />
        ))}
      </TableRow>
    </TableHeader>
  );

  if (isPersonTab && byCourse) {
    if (isBackToBackConflictType(activeTabId)) {
      return (
        <p className="py-6 text-sm text-muted-foreground">
          Back-to-back conflicts don't record which exams are involved yet, so
          they can't be counted per course.
        </p>
      );
    }
    const summaries = summarizeConflictsByCourse(rowsForActive);
    const sorted = sort
      ? sortCourseSummaries(summaries, sort as SortState<CourseSortColumn>)
      : summaries;
    const courseBar = { ...pagination, total: sorted.length, noun: " courses" };
    return (
      <>
        {isPerDayLimitConflictType(activeTabId) && (
          <p className="text-sm text-muted-foreground">
            Counts only the exam that put each person over the daily limit;
            their other exams that day aren't recorded.
          </p>
        )}
        <PaginationBar {...courseBar} onPageSize={onPageSize} />
        <Table className="min-w-3xl table-fixed">
          {header([
            { id: "course", label: "Course" },
            { id: "crn", label: "CRN" },
            {
              id: "people",
              label: `${isInstructorTab ? "Instructors" : "Students"} with a conflict`,
            },
            { id: "conflictCount", label: "Conflicts" },
          ])}
          <TableBody>
            {sorted.slice(start, start + pageSize).map((s) => (
              <TableRow key={s.crn || s.course}>
                <TableCell className="font-medium">{s.course || "—"}</TableCell>
                <TableCell className="tabular-nums">{s.crn || "—"}</TableCell>
                <TableCell className="tabular-nums">
                  {s.people.length}
                </TableCell>
                <TableCell className="tabular-nums">
                  {s.conflictCount}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        <PaginationBar {...courseBar} />
      </>
    );
  }

  if (!isPersonTab) {
    const records = rowsForActive.filter(
      (r): r is RecordConflictRow => r.kind === "record",
    );
    const hiddenColumns = HIDDEN_RECORD_COLUMNS[activeTabId] ?? [];
    const recordColumns = (
      [
        { key: "entity", label: entityLabel },
        { key: "day", label: "Day" },
        { key: "block", label: "Block" },
        { key: "course", label: "Course" },
        { key: "crn", label: "CRN" },
        { key: "size", label: "Size" },
      ] satisfies { key: RecordSortColumn; label: string }[]
    ).filter(
      (c) =>
        !hiddenColumns.includes(c.key) &&
        records.some((r) => r[c.key] != null && String(r[c.key]).trim() !== ""),
    );
    const sorted = sort
      ? sortRecordRows(records, sort as SortState<RecordSortColumn>)
      : records;
    const recordBar = { ...pagination, total: sorted.length, noun: "" };
    return (
      <>
        <PaginationBar {...recordBar} onPageSize={onPageSize} />
        <Table className="min-w-3xl table-fixed">
          {header(recordColumns.map((c) => ({ id: c.key, label: c.label })))}
          <TableBody>
            {sorted.slice(start, start + pageSize).map((r) => (
              <TableRow key={r.id} className="align-top">
                {recordColumns.map((c) => (
                  <TableCell key={c.key}>{r[c.key] || "—"}</TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
        <PaginationBar {...recordBar} />
      </>
    );
  }

  const people = rowsForActive.filter(
    (r): r is PersonConflictRow => r.kind === "person",
  );
  const personSort = sort && PERSON_SORT_COLUMNS[sort.column];
  const sorted =
    sort && personSort
      ? sortPersonRows(people, {
          column: personSort,
          direction: sort.direction,
        })
      : people;

  // Back-to-back records carry only time slots (no courses): show the slots
  // as pills instead of an always-empty exams column.
  const showCourses = people.some((r) =>
    r.instances.some((i) => i.courses.length),
  );
  // Per-day limit records name only the exam that went over the limit, not
  // the day's other exams (EXENG-46): list just the days over the limit.
  const isPerDayTab = isPerDayLimitConflictType(activeTabId);

  // Percentage widths so columns spread with the table instead of bunching
  // left, while staying independent of page contents. The last column takes
  // the rest; it is sortable only when it is not a column of pills.
  const columns: TableColumn[] = isPerDayTab
    ? [
        { id: "entity", label: entityLabel, width: "w-[18%]" },
        { id: "conflictCount", label: "Days over limit", width: "w-[15%]" },
        { id: "day", label: "Day" },
      ]
    : showCourses
      ? [
          { id: "entity", label: entityLabel, width: "w-[15%]" },
          { id: "conflictCount", label: "Conflicts", width: "w-[10%]" },
          { id: "day", label: "Day", width: "w-[12%]" },
          { id: "time", label: "Time", width: "w-[15%]" },
          { label: "Conflicting exams" },
        ]
      : [
          { id: "entity", label: entityLabel, width: "w-[18%]" },
          { id: "conflictCount", label: "Conflicts", width: "w-[12%]" },
          { id: "day", label: "Day", width: "w-[15%]" },
          { label: "Exam times" },
        ];
  const showTimeColumn = showCourses && !isPerDayTab;
  const personBar = { ...pagination, total: sorted.length, noun: peopleNoun };

  return (
    <>
      <PaginationBar {...personBar} onPageSize={onPageSize} />
      <Table className="min-w-3xl table-fixed">
        {header(columns)}
        <TableBody>
          {sorted.slice(start, start + pageSize).map((r) => {
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
                      {r.entity ? (
                        <span className="inline-flex items-center gap-1">
                          {r.entity}
                          <CopyButton
                            value={r.entity}
                            label={`Copy ${isInstructorTab ? "instructor" : "NUId"} ${r.entity}`}
                          />
                        </span>
                      ) : (
                        "—"
                      )}
                    </TableCell>
                    <TableCell rowSpan={span} className="align-top">
                      {r.conflictCount}
                    </TableCell>
                  </>
                )}
                <TableCell className="align-top">{inst.day || "—"}</TableCell>
                {showTimeColumn && (
                  <TableCell className="align-top tabular-nums">
                    {inst.time || "—"}
                  </TableCell>
                )}
                {!isPerDayTab && (
                  <TableCell className="align-top whitespace-normal">
                    <div className="flex flex-wrap gap-1">
                      {showCourses
                        ? inst.courses.map((c) => (
                            <CoursePill
                              key={c.crn || c.course}
                              course={c}
                              onOpen={onOpenCourse}
                            />
                          ))
                        : // A time repeats when the person also has two exams
                          // in that block; show it twice, keyed by position.
                          inst.slots.map((slot, slotIdx) => (
                            <Badge
                              key={`${slotIdx}-${slot}`}
                              variant="secondary"
                              className="w-32 tabular-nums"
                            >
                              {slot}
                            </Badge>
                          ))}
                      {showCourses && inst.courses.length === 0 && "—"}
                    </div>
                  </TableCell>
                )}
              </TableRow>
            ));
          })}
        </TableBody>
      </Table>
      <PaginationBar {...personBar} />
    </>
  );
}

// Conflict View: summary cards and rows from the saved conflict breakdown.
// `type` selects the conflict tab (from the URL); an unknown or absent type
// shows the first tab.
export default function ConflictView({
  type,
  onTypeChange,
}: {
  type: string | null;
  onTypeChange: (type: string) => void;
}) {
  const { rowsByType, types } = useConflictDataSimple();
  // Card counts come from the server's summary (same as the Statistics tab).
  const conflicts = useSchedulesStore(
    (state) => state.currentSchedule?.summary?.conflicts,
  );

  // Same order as the tabs: students, instructors, then courses. Who is
  // affected goes in a pill under the title so titles stay on one line.
  const summaryCards = [
    {
      audience: "Student",
      label: "Double-Book",
      metric: "student_double_book",
      subtitle: "Students with overlapping exams",
      icon: <UserX className="h-4 w-4" />,
      tone: "destructive",
    },
    {
      audience: "Student",
      label: "Per-Day Limit",
      metric: "student_over_daily_limit",
      subtitle: "Students over the daily exam limit",
      icon: <Calendar className="h-4 w-4" />,
      tone: "destructive",
    },
    {
      audience: "Student",
      label: "Back-to-Back",
      metric: "student_back_to_back",
      subtitle: "Students with back-to-back exams",
      icon: <Clock className="h-4 w-4" />,
      tone: "warning",
    },
    {
      audience: "Instructor",
      label: "Double-Book",
      metric: "instructor_double_book",
      subtitle: "Instructors with overlapping exams",
      icon: <Briefcase className="h-4 w-4" />,
      tone: "destructive",
    },
    {
      audience: "Instructor",
      label: "Per-Day Limit",
      metric: "instructor_over_daily_limit",
      subtitle: "Instructors over the daily exam limit",
      icon: <CalendarX className="h-4 w-4" />,
      tone: "destructive",
    },
    {
      audience: "Instructor",
      label: "Back-to-Back",
      metric: "instructor_back_to_back",
      subtitle: "Instructors with back-to-back exams",
      icon: <GraduationCap className="h-4 w-4" />,
      tone: "warning",
    },
    {
      audience: "Course",
      label: "Large, Not Early",
      metric: "large_courses_late",
      subtitle: "100+ enrollment scheduled late",
      icon: <AlertTriangle className="h-4 w-4" />,
      tone: "warning",
    },
  ] as const;

  // Students first, then instructors, then courses; unlisted types last.
  const effectiveTabs = [
    ...(types.length > 0 ? types : ["back_to_back", "large_course_not_early"]),
  ]
    .sort((a, b) => conflictTypeRank(a) - conflictTypeRank(b))
    .map((t) => ({ id: t, label: conflictTypeMap[t] ?? t }));

  const [pageByTab, setPageByTab] = useState<Record<string, number>>({});

  function setPage(tabId: string, page: number) {
    setPageByTab((s) => ({ ...s, [tabId]: page }));
  }

  function getPage(tabId: string) {
    return pageByTab[tabId] ?? 0;
  }

  const pageSize = useConflictViewStore((s) => s.pageSize);
  const setPageSize = useConflictViewStore((s) => s.setPageSize);

  const activeTab =
    effectiveTabs.find((t) => t.id === type)?.id ??
    effectiveTabs[0]?.id ??
    "back_to_back";

  const rowsForActive = rowsByType[activeTab] ?? [];
  const page = getPage(activeTab);

  // "By course" applies to every person tab until switched back.
  const [byCourse, setByCourse] = useState(false);
  const [openCourse, setOpenCourse] = useState<ConflictCourse | null>(null);
  const isPersonTab = isPersonConflictType(activeTab);
  const showByCourse = isPersonTab && byCourse;

  // Sort per tab and per view; switching tabs or views keeps each one's sort.
  const [sortByView, setSortByView] = useState<
    Record<string, SortState<string>>
  >({});
  const viewKey = `${activeTab}|${showByCourse ? "course" : "rows"}`;
  const sort =
    sortByView[viewKey] ?? (showByCourse ? DEFAULT_COURSE_SORT : undefined);

  function toggleSort(column: string) {
    const direction =
      sort?.column === column && sort.direction === "asc" ? "desc" : "asc";
    setSortByView((s) => ({ ...s, [viewKey]: { column, direction } }));
    setPage(activeTab, 0);
  }

  function chooseByCourse(next: boolean) {
    setByCourse(next);
    setPage(activeTab, 0);
  }

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

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-4 lg:grid-cols-7">
        {summaryCards.map((c) => {
          const value = conflicts?.[c.metric].people ?? 0;
          return (
            <ConflictStat
              key={c.metric}
              label={c.label}
              audience={c.audience}
              value={value}
              icon={c.icon}
              subtitle={c.subtitle}
              variant={value > 0 ? c.tone : "success"}
            />
          );
        })}
      </div>

      <div className="mt-4">
        <div className="flex gap-2">
          {effectiveTabs.map((t) => (
            <Button
              key={t.id}
              onClick={() => {
                onTypeChange(t.id);
                setPage(t.id, 0);
              }}
              aria-pressed={activeTab === t.id}
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
              {isPersonTab && (
                <CardAction>
                  <ButtonGroup aria-label="Group conflicts">
                    {[
                      {
                        value: false,
                        label: isInstructorConflictType(activeTab)
                          ? "By instructor"
                          : "By student",
                      },
                      { value: true, label: "By course" },
                    ].map(({ value, label }) => (
                      <Button
                        key={label}
                        size="sm"
                        variant={byCourse === value ? "default" : "outline"}
                        aria-pressed={byCourse === value}
                        onClick={() => chooseByCourse(value)}
                      >
                        {label}
                      </Button>
                    ))}
                  </ButtonGroup>
                </CardAction>
              )}
            </CardHeader>
            <CardContent>
              <ConflictTable
                rowsForActive={rowsForActive}
                activeTabId={activeTab}
                byCourse={showByCourse}
                sort={sort}
                onSort={toggleSort}
                page={page}
                onPage={(p) => setPage(activeTab, p)}
                pageSize={pageSize}
                onOpenCourse={setOpenCourse}
                onPageSize={(size) => {
                  setPageSize(size);
                  // Old page indexes are meaningless at the new size.
                  setPageByTab({});
                }}
              />
            </CardContent>
          </Card>

          <ConflictDefinitions />
          <CourseConflictDialog
            course={openCourse}
            rowsByType={rowsByType}
            onClose={() => setOpenCourse(null)}
          />
        </div>
      </div>
    </section>
  );
}
