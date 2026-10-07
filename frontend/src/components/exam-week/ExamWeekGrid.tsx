import { cn } from "@/lib/utils";
import { examsBySlot, slotKey, type WeekExam } from "./examWeek";

/**
 * The schedule's exam week (days across, blocks down) with each scheduled
 * exam blocked out; unscheduled exams are left out. Blocks in a
 * `doubleBooked` slot are red.
 */
export function ExamWeekGrid({
  days,
  blockTimes,
  exams,
  doubleBooked,
}: {
  days: string[];
  blockTimes: string[];
  exams: WeekExam[];
  doubleBooked?: ReadonlySet<string>;
}) {
  const perSlot = examsBySlot(exams);
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
                const key = slotKey(dayIndex, block);
                const slotExams = perSlot.get(key) ?? [];
                return (
                  <td
                    key={day}
                    className="h-14 border p-1 align-top"
                    data-testid={`week-${dayIndex}-${block}`}
                  >
                    <div className="space-y-1">
                      {slotExams.map((exam) => (
                        <ExamBlock
                          key={`${exam.crn}-${exam.proposed ? "proposed" : ""}`}
                          exam={exam}
                          doubleBooked={!!doubleBooked?.has(key)}
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
  exam: WeekExam;
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
