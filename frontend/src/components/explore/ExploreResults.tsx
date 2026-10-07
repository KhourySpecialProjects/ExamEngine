import { CalendarDays, GitMerge, Layers, List } from "lucide-react";
import type { ReactNode } from "react";
import { Collapsible } from "@/components/common/Collapsible";
import { type ExamColumn, ExamTable } from "@/components/exam-week/ExamTable";
import {
  BLOCKED_SLOT_CLASS,
  ExamWeekGrid,
} from "@/components/exam-week/ExamWeekGrid";
import { type ExamGroups, withGroups } from "@/components/exam-week/examGroups";
import {
  byWeek,
  doubleBookedSlots,
  examsBySlot,
  slotKey,
  slotOf,
  type WeekExam,
} from "@/components/exam-week/examWeek";
import { Button } from "@/components/ui/button";
import { ButtonGroup } from "@/components/ui/button-group";
import type {
  BlockedSlot,
  ScheduleExam,
  ScheduleRoomsResult,
} from "@/lib/api/schedules";
import { cn } from "@/lib/utils";
import { weekExam } from "./scheduleRows";

export type ExploreDisplay = "calendar" | "list";

export function examCount(count: number): string {
  return `${count} exam${count === 1 ? "" : "s"}`;
}

/** Calendar / List switch. */
export function DisplaySwitch({
  display,
  onChange,
}: {
  display: ExploreDisplay;
  onChange: (display: ExploreDisplay) => void;
}) {
  return (
    <ButtonGroup aria-label="Show as">
      {(
        [
          { value: "calendar", label: "Calendar", icon: CalendarDays },
          { value: "list", label: "List", icon: List },
        ] as const
      ).map(({ value, label, icon: Icon }) => (
        <Button
          key={value}
          size="sm"
          variant={display === value ? "default" : "outline"}
          aria-pressed={display === value}
          onClick={() => onChange(value)}
        >
          <Icon className="size-4" aria-hidden />
          {label}
        </Button>
      ))}
    </ButtonGroup>
  );
}

/** A room's blocked slots, and whether the blockouts file could be read. */
export interface RoomBlockouts {
  slots: BlockedSlot[];
  status: ScheduleRoomsResult["blockouts"];
}

const BLOCKOUTS_NOTE: Record<RoomBlockouts["status"], string | null> = {
  ok: null,
  none_uploaded: "No room blockouts file was uploaded with this dataset.",
  unavailable:
    "Blocked times are unavailable: the dataset's room blockouts file can't be read.",
};

/**
 * What was looked up (`heading`) and its exams as the exam week or a list.
 * Unscheduled exams only appear in the list; the calendar says how many.
 * Exams get their combined / common group from `groups`; a common badge
 * lists the group's sections from the schedule's `rows`. With
 * `markDoubleBooks` (people) a slot with two different exams is red. A
 * room's `blockouts` are striped on the calendar and listed (collapsed)
 * under the list.
 */
export function ExploreResults({
  heading,
  exams: plainExams,
  days,
  blockTimes,
  display,
  columns,
  groups,
  rows,
  markDoubleBooks = false,
  blockouts,
  onInstructorClick,
  onRoomClick,
  emptyText,
}: {
  heading: ReactNode;
  /** In week order (`byWeek`). */
  exams: WeekExam[];
  days: string[];
  blockTimes: string[];
  display: ExploreDisplay;
  columns: ExamColumn[];
  groups: ExamGroups;
  /** The schedule's exam list, for a common group's sections. */
  rows: ScheduleExam[];
  markDoubleBooks?: boolean;
  blockouts?: RoomBlockouts;
  onInstructorClick?: (instructorId: string) => void;
  onRoomClick?: (room: string) => void;
  emptyText: string;
}) {
  const exams = plainExams.map((exam) => withGroups(exam, groups));
  const commonSections = (label: string) => {
    const crns = new Set(groups.commonCrns.get(label));
    return rows
      .filter((row) => crns.has(row.CRN.trim()))
      .map((row) => withGroups(weekExam(row, days, blockTimes), groups))
      .sort(byWeek);
  };
  const doubleBooked = markDoubleBooks
    ? doubleBookedSlots(examsBySlot(exams))
    : undefined;
  const unscheduled = exams.filter((exam) => slotOf(exam) == null).length;
  const blockedSlots = blockouts?.slots ?? [];
  const blocked = new Set(blockedSlots.map((s) => slotKey(s.day, s.block)));
  const examInBlockedSlot = exams.some((exam) => {
    const slot = slotOf(exam);
    return slot != null && blocked.has(slot);
  });
  const blockoutsNote = blockouts && BLOCKOUTS_NOTE[blockouts.status];
  // Blocked blocks the schedule doesn't use (e.g. 6PM in a 4-block schedule).
  const blockedOutsideWeek = blockedSlots.filter(
    (s) => s.day >= days.length || s.block >= blockTimes.length,
  ).length;
  const legend: LegendEntries = {
    blocked: blockedSlots.length > 0,
    examInBlockedSlot,
    doubleBooked: (doubleBooked?.size ?? 0) > 0,
    combined: exams.some((exam) => slotOf(exam) && exam.combined),
    common: exams.some((exam) => slotOf(exam) && exam.common),
  };
  return (
    <section aria-label="Results" className="space-y-3">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        {heading}
        <span className="text-sm text-muted-foreground">
          {examCount(exams.length)}
          {unscheduled > 0 && `, ${unscheduled} unscheduled`}
          {blockouts?.status === "ok" &&
            `, ${blockedSlots.length} blocked slot${blockedSlots.length === 1 ? "" : "s"}`}
        </span>
      </div>
      {display === "calendar" ? (
        exams.length === 0 && blockedSlots.length === 0 ? (
          <p className="text-sm text-muted-foreground">{emptyText}</p>
        ) : (
          <>
            <ExamWeekGrid
              days={days}
              blockTimes={blockTimes}
              exams={exams}
              doubleBooked={doubleBooked}
              blocked={blocked}
              onRoomClick={onRoomClick}
              commonSections={commonSections}
            />
            {Object.values(legend).some(Boolean) && <Legend {...legend} />}
            {unscheduled > 0 && (
              <p className="text-sm text-muted-foreground">
                {examCount(unscheduled)} unscheduled, so not on the calendar:
                see List.
              </p>
            )}
            {blockedOutsideWeek > 0 && (
              <p className="text-sm text-muted-foreground">
                {blockedOutsideWeek} blocked slot
                {blockedOutsideWeek === 1 ? " is" : "s are"} outside this
                schedule's exam week: see List.
              </p>
            )}
          </>
        )
      ) : (
        <>
          {exams.length === 0 ? (
            <p className="text-sm text-muted-foreground">{emptyText}</p>
          ) : (
            <ExamTable
              exams={exams}
              columns={columns}
              doubleBooked={doubleBooked}
              blocked={blocked}
              onInstructorClick={onInstructorClick}
              onRoomClick={onRoomClick}
              commonSections={commonSections}
            />
          )}
          {blockedSlots.length > 0 && (
            <Collapsible summary={`Blocked times (${blockedSlots.length})`}>
              <ul className="space-y-0.5 text-muted-foreground">
                {blockedSlots.map((s) => (
                  <li key={slotKey(s.day, s.block)}>
                    {s.day_name} {s.block_time}
                  </li>
                ))}
              </ul>
            </Collapsible>
          )}
        </>
      )}
      {blockoutsNote && (
        <p className="text-sm text-muted-foreground">{blockoutsNote}</p>
      )}
    </section>
  );
}

/** Which marks the calendar shows, so the legend only explains those. */
interface LegendEntries {
  blocked: boolean;
  examInBlockedSlot: boolean;
  doubleBooked: boolean;
  combined: boolean;
  common: boolean;
}

function Legend({
  blocked,
  examInBlockedSlot,
  doubleBooked,
  combined,
  common,
}: LegendEntries) {
  const swatch = "inline-block size-3 rounded-sm border";
  const red = cn(swatch, "border-destructive bg-destructive/10");
  const item = "inline-flex items-center gap-1.5";
  return (
    <ul
      aria-label="Legend"
      className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground"
    >
      <li className={item}>
        <span className={cn(swatch, "border-blue-300 bg-blue-50")} />
        Exam
      </li>
      {combined && (
        <li className={item}>
          <GitMerge className="size-3 text-blue-700" aria-hidden />
          Combined exam (sections share a room)
        </li>
      )}
      {common && (
        <li className={item}>
          <Layers className="size-3 text-violet-700" aria-hidden />
          Common exam (same block, other rooms)
        </li>
      )}
      {doubleBooked && (
        <li className={item}>
          <span className={red} />
          Double-booked
        </li>
      )}
      {blocked && (
        <li className={item}>
          <span
            className={cn(swatch, "border-orange-200", BLOCKED_SLOT_CLASS)}
          />
          Blocked (room not available)
        </li>
      )}
      {examInBlockedSlot && (
        <li className={item}>
          <span className={red} />
          Exam in a blocked slot
        </li>
      )}
    </ul>
  );
}
