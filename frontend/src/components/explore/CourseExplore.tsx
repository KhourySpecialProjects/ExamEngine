import { Loader2 } from "lucide-react";
import { type ReactNode, useMemo } from "react";
import { byWeek } from "@/components/exam-week/examWeek";
import type { ScheduleExam, ScheduleResult } from "@/lib/api/schedules";
import type { ScheduleRoomsState } from "@/lib/hooks/useScheduleRooms";
import { type ExploreDisplay, ExploreResults } from "./ExploreResults";
import { LookupCombobox, type LookupOption } from "./LookupCombobox";
import { weekExam } from "./scheduleRows";

/** Course codes ("CS 2000", with their section count) and CRNs (with their course). */
export function courseOptions(rows: ScheduleExam[]): LookupOption[] {
  const sections = new Map<string, number>();
  for (const row of rows) {
    sections.set(row.Course, (sections.get(row.Course) ?? 0) + 1);
  }
  const codes = [...sections]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([value, count]) => ({
      value,
      detail: `${count} section${count === 1 ? "" : "s"}`,
    }));
  const crns = rows
    .map((row) => ({ value: row.CRN, detail: row.Course }))
    .sort((a, b) => a.value.localeCompare(b.value));
  return [...codes, ...crns];
}

/**
 * Explore a course: a CRN shows its exam, a course code all its sections'
 * exams. The value is in the URL (`q`). The week to draw comes with the
 * schedule's rooms.
 */
export function CourseExplore({
  schedule,
  course,
  rooms,
  display,
  toolbar,
  onCourseChange,
  onInstructorClick,
  onRoomClick,
}: {
  schedule: ScheduleResult;
  /** A CRN or a course code. */
  course: string | null;
  rooms: ScheduleRoomsState;
  display: ExploreDisplay;
  /** Shown at the end of the lookup row (the Calendar / List switch). */
  toolbar: ReactNode;
  onCourseChange: (course: string) => void;
  onInstructorClick: (instructorId: string) => void;
  onRoomClick: (room: string) => void;
}) {
  const rows = schedule.schedule.complete;
  const options = useMemo(() => courseOptions(rows), [rows]);
  const week = rooms.result;
  // A CRN wins over a course code of the same text.
  const { isCrn, matched } = useMemo(() => {
    const byCrn = rows.filter((row) => row.CRN === course);
    return byCrn.length > 0
      ? { isCrn: true, matched: byCrn }
      : { isCrn: false, matched: rows.filter((row) => row.Course === course) };
  }, [rows, course]);
  const exams = useMemo(
    () =>
      week
        ? matched
            .map((row) => weekExam(row, week.days, week.block_times))
            .sort(byWeek)
        : [],
    [matched, week],
  );
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <LookupCombobox
          label="Course"
          options={options}
          value={course}
          onSelect={onCourseChange}
          placeholder="Choose a CRN or course…"
          searchPlaceholder="Search CRNs and course codes..."
          emptyText="No CRN or course found."
          limit={100}
        />
        {toolbar}
      </div>

      {!course && (
        <p className="text-sm text-muted-foreground">
          Choose a CRN to see when its exam is, or a course code to see all its
          sections.
        </p>
      )}
      {course && matched.length === 0 && (
        <p className="text-sm text-muted-foreground">
          No CRN or course “{course}” in this schedule.
        </p>
      )}
      {course && matched.length > 0 && rooms.isLoading && (
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading…
        </p>
      )}
      {rooms.error && (
        <p role="alert" className="text-sm text-destructive">
          {rooms.error}
        </p>
      )}
      {course && matched.length > 0 && week && (
        <ExploreResults
          heading={
            <h3 className="flex items-baseline gap-1.5 font-semibold">
              {isCrn ? (
                <>
                  CRN <span className="font-mono">{course}</span>
                  <span className="font-normal">· {matched[0].Course}</span>
                </>
              ) : (
                <>Course {course}</>
              )}
            </h3>
          }
          exams={exams}
          days={week.days}
          blockTimes={week.block_times}
          display={display}
          columns={[
            "day",
            "time",
            "crn",
            "course",
            "room",
            "instructor",
            "size",
          ]}
          onInstructorClick={onInstructorClick}
          onRoomClick={onRoomClick}
          emptyText="No exams."
        />
      )}
    </div>
  );
}
