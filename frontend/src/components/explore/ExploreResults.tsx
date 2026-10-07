import { CalendarDays, List } from "lucide-react";
import type { ReactNode } from "react";
import { type ExamColumn, ExamTable } from "@/components/exam-week/ExamTable";
import { ExamWeekGrid } from "@/components/exam-week/ExamWeekGrid";
import { slotOf, type WeekExam } from "@/components/exam-week/examWeek";
import { Button } from "@/components/ui/button";
import { ButtonGroup } from "@/components/ui/button-group";

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

/**
 * What was looked up (`heading`) and its exams as the exam week or a list.
 * Unscheduled exams only appear in the list; the calendar says how many.
 */
export function ExploreResults({
  heading,
  exams,
  days,
  blockTimes,
  display,
  columns,
  doubleBooked,
  onInstructorClick,
  emptyText,
}: {
  heading: ReactNode;
  /** In week order (`byWeek`). */
  exams: WeekExam[];
  days: string[];
  blockTimes: string[];
  display: ExploreDisplay;
  columns: ExamColumn[];
  doubleBooked?: ReadonlySet<string>;
  onInstructorClick?: (instructorId: string) => void;
  emptyText: string;
}) {
  const unscheduled = exams.filter((exam) => slotOf(exam) == null).length;
  return (
    <section aria-label="Results" className="space-y-3">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        {heading}
        <span className="text-sm text-muted-foreground">
          {examCount(exams.length)}
          {unscheduled > 0 && `, ${unscheduled} unscheduled`}
        </span>
      </div>
      {exams.length === 0 ? (
        <p className="text-sm text-muted-foreground">{emptyText}</p>
      ) : display === "calendar" ? (
        <>
          <ExamWeekGrid
            days={days}
            blockTimes={blockTimes}
            exams={exams}
            doubleBooked={doubleBooked}
          />
          {unscheduled > 0 && (
            <p className="text-sm text-muted-foreground">
              {examCount(unscheduled)} unscheduled, so not on the calendar: see
              List.
            </p>
          )}
        </>
      ) : (
        <ExamTable
          exams={exams}
          columns={columns}
          doubleBooked={doubleBooked}
          onInstructorClick={onInstructorClick}
        />
      )}
    </section>
  );
}
