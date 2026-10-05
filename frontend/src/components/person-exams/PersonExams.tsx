import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { PersonExam, PersonExamsResult } from "@/lib/api/schedules";
import { cn } from "@/lib/utils";

/** An exam as shown: `proposed` marks a late-add candidate not in the schedule. */
interface ShownExam extends PersonExam {
  proposed?: boolean;
}

function slotOf(exam: PersonExam): string | null {
  return exam.day != null && exam.block != null
    ? `${exam.day}-${exam.block}`
    : null;
}

/** Same order as the API (by day and block, then unscheduled), proposed last in its block. */
function byWeek(a: ShownExam, b: ShownExam): number {
  return (
    Number(a.day == null) - Number(b.day == null) ||
    (a.day ?? 0) - (b.day ?? 0) ||
    (a.block ?? 0) - (b.block ?? 0) ||
    Number(!!a.proposed) - Number(!!b.proposed) ||
    a.crn.localeCompare(b.crn)
  );
}

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
  const exams: ShownExam[] = [
    ...result.exams,
    ...(proposed ? [{ ...proposed, proposed: true }] : []),
  ].sort(byWeek);
  const perSlot = new Map<string, ShownExam[]>();
  for (const exam of exams) {
    const slot = slotOf(exam);
    if (slot) perSlot.set(slot, [...(perSlot.get(slot) ?? []), exam]);
  }
  const isDoubleBooked = (exam: PersonExam) => {
    const slot = slotOf(exam);
    return slot != null && (perSlot.get(slot)?.length ?? 0) > 1;
  };

  if (exams.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No exams for this {result.kind} in this schedule.
      </p>
    );
  }
  return (
    <div className="space-y-4">
      <ExamList exams={exams} isDoubleBooked={isDoubleBooked} />
      {perSlot.size > 0 && (
        <ExamWeek
          days={result.days}
          blockTimes={result.block_times}
          perSlot={perSlot}
        />
      )}
    </div>
  );
}

function ExamList({
  exams,
  isDoubleBooked,
}: {
  exams: ShownExam[];
  isDoubleBooked: (exam: PersonExam) => boolean;
}) {
  // Short list: it scrolls on its own so the week below stays in view.
  return (
    <div className="max-h-56 overflow-y-auto rounded-md border">
      <Table aria-label="Exams" className="[&_td]:py-1 [&_th]:h-8">
        <TableHeader className="sticky top-0 bg-background">
          <TableRow>
            <TableHead>Day</TableHead>
            <TableHead>Time</TableHead>
            <TableHead>CRN</TableHead>
            <TableHead>Course</TableHead>
            <TableHead>Room</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {exams.map((exam) => {
            const scheduled = slotOf(exam) != null;
            return (
              <TableRow key={`${exam.crn}-${exam.proposed ? "proposed" : ""}`}>
                <TableCell
                  className={cn(!scheduled && "text-muted-foreground")}
                >
                  {exam.day_name ?? "Unscheduled"}
                </TableCell>
                <TableCell>
                  <span className="inline-flex items-center gap-1.5">
                    {exam.block_time ?? "—"}
                    {isDoubleBooked(exam) && (
                      <Badge variant="destructive">Double-booked</Badge>
                    )}
                  </span>
                </TableCell>
                <TableCell>
                  <span className="inline-flex items-center gap-1.5 font-mono">
                    {exam.crn}
                    {exam.proposed && (
                      <Badge
                        variant="outline"
                        className="border-dashed font-sans"
                      >
                        Proposed
                      </Badge>
                    )}
                  </span>
                </TableCell>
                <TableCell>{exam.course_code}</TableCell>
                <TableCell
                  className={cn(
                    "font-mono",
                    !exam.room && "text-muted-foreground",
                  )}
                >
                  {exam.room ?? (scheduled ? "No room" : "—")}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}

function ExamWeek({
  days,
  blockTimes,
  perSlot,
}: {
  days: string[];
  blockTimes: string[];
  perSlot: Map<string, ShownExam[]>;
}) {
  return (
    <div className="overflow-x-auto">
      <table
        aria-label="Exam week"
        className="w-full min-w-[32rem] table-fixed border-collapse text-xs"
      >
        <thead>
          <tr>
            <th className="w-28 border bg-muted/50 p-1.5" aria-label="Time" />
            {days.map((day) => (
              <th
                key={day}
                scope="col"
                className="border bg-muted/50 p-1.5 font-semibold"
              >
                {day}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {blockTimes.map((time, block) => (
            <tr key={time}>
              <th
                scope="row"
                className="border bg-muted/50 p-1.5 text-left font-medium whitespace-nowrap"
              >
                {time}
              </th>
              {days.map((day, dayIndex) => {
                const exams = perSlot.get(`${dayIndex}-${block}`) ?? [];
                return (
                  <td
                    key={day}
                    className="h-14 border p-1 align-top"
                    data-testid={`week-${dayIndex}-${block}`}
                  >
                    <div className="space-y-1">
                      {exams.map((exam) => (
                        <ExamBlock
                          key={`${exam.crn}-${exam.proposed ? "proposed" : ""}`}
                          exam={exam}
                          doubleBooked={exams.length > 1}
                        />
                      ))}
                    </div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ExamBlock({
  exam,
  doubleBooked,
}: {
  exam: ShownExam;
  doubleBooked: boolean;
}) {
  const room = exam.room ?? "No room";
  const notes = [
    exam.proposed && "proposed late add",
    doubleBooked && "double-booked",
  ].filter(Boolean);
  return (
    <div
      title={[
        `CRN ${exam.crn} · ${exam.course_code}`,
        `Room: ${room}`,
        ...notes,
      ].join("\n")}
      className={cn(
        "rounded border px-1.5 py-1 leading-tight",
        doubleBooked
          ? "border-destructive bg-destructive/10 text-destructive"
          : "border-blue-300 bg-blue-50 text-blue-950",
        exam.proposed && "border-dashed",
      )}
    >
      <div className="font-mono font-semibold">{exam.crn}</div>
      <div className="truncate">{exam.course_code}</div>
      <div
        className={cn(
          "truncate font-mono",
          !doubleBooked && "text-muted-foreground",
        )}
      >
        {room}
      </div>
      {exam.proposed && <div className="italic">Proposed</div>}
    </div>
  );
}
