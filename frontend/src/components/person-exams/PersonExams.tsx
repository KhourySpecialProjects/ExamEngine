import { ExamTable } from "@/components/exam-week/ExamTable";
import { ExamWeekGrid } from "@/components/exam-week/ExamWeekGrid";
import {
  byWeek,
  doubleBookedSlots,
  examsBySlot,
  type WeekExam,
} from "@/components/exam-week/examWeek";
import type { PersonExam, PersonExamsResult } from "@/lib/api/schedules";

/**
 * One person's exams: a short list, then the schedule's exam week with each
 * exam blocked out. Two or more exams in one block (a double-book) are red.
 * `proposed` is a late-add candidate, drawn dashed.
 */
export function PersonExams({
  result,
  proposed,
}: {
  result: PersonExamsResult;
  proposed?: PersonExam | null;
}) {
  const exams: WeekExam[] = [
    ...result.exams,
    ...(proposed ? [{ ...proposed, proposed: true }] : []),
  ].sort(byWeek);
  const perSlot = examsBySlot(exams);

  if (exams.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No exams for this {result.kind} in this schedule.
      </p>
    );
  }
  const doubleBooked = doubleBookedSlots(perSlot);
  return (
    <div className="space-y-4">
      {/* Short list: it scrolls on its own so the week below stays in view. */}
      <ExamTable
        exams={exams}
        doubleBooked={doubleBooked}
        className="max-h-56 overflow-y-auto"
      />
      {perSlot.size > 0 && (
        <ExamWeekGrid
          days={result.days}
          blockTimes={result.block_times}
          exams={exams}
          doubleBooked={doubleBooked}
        />
      )}
    </div>
  );
}
