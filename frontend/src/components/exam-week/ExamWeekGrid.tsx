import { Ban } from "lucide-react";
import { cn } from "@/lib/utils";
import { examsBySlot, slotKey, type WeekExam } from "./examWeek";
import { Pivot } from "./Pivot";

/** Diagonal orange stripes: the look of a blocked slot (also in the legend). */
export const BLOCKED_SLOT_CLASS =
  "bg-[repeating-linear-gradient(135deg,var(--color-orange-100)_0_6px,var(--color-orange-50)_6px_12px)]";

/**
 * The schedule's exam week (days across, blocks down) with each scheduled
 * exam blocked out; unscheduled exams are left out. Blocks in a
 * `doubleBooked` slot are red. `blocked` slots are striped orange, and an
 * exam inside one is red. With `onRoomClick` an exam's room is a link.
 */
export function ExamWeekGrid({
  days,
  blockTimes,
  exams,
  doubleBooked,
  blocked,
  onRoomClick,
}: {
  days: string[];
  blockTimes: string[];
  exams: WeekExam[];
  doubleBooked?: ReadonlySet<string>;
  blocked?: ReadonlySet<string>;
  onRoomClick?: (room: string) => void;
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
                const isBlocked = !!blocked?.has(key);
                return (
                  <td
                    key={day}
                    className={cn(
                      "h-14 border p-1 align-top",
                      isBlocked && BLOCKED_SLOT_CLASS,
                    )}
                    data-testid={`week-${dayIndex}-${block}`}
                  >
                    <div className="space-y-1">
                      {isBlocked && (
                        <div className="flex items-center gap-1 font-medium text-orange-800">
                          <Ban className="size-3" aria-hidden />
                          Blocked
                        </div>
                      )}
                      {slotExams.map((exam) => (
                        <ExamBlock
                          key={`${exam.crn}-${exam.proposed ? "proposed" : ""}`}
                          exam={exam}
                          doubleBooked={!!doubleBooked?.has(key)}
                          inBlockedSlot={isBlocked}
                          onRoomClick={onRoomClick}
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
  inBlockedSlot,
  onRoomClick,
}: {
  exam: WeekExam;
  doubleBooked: boolean;
  inBlockedSlot: boolean;
  onRoomClick?: (room: string) => void;
}) {
  const examRoom = exam.room;
  const room = examRoom ?? "No room";
  const notes = [
    exam.proposed && "proposed late add",
    doubleBooked && "double-booked",
    inBlockedSlot && "in a blocked slot",
  ].filter(Boolean);
  const red = doubleBooked || inBlockedSlot;
  return (
    <div
      title={[
        `CRN ${exam.crn} · ${exam.course_code}`,
        `Room: ${room}`,
        ...notes,
      ].join("\n")}
      className={cn(
        "rounded border px-1.5 py-1 leading-tight",
        red
          ? "border-destructive bg-destructive/10 text-destructive"
          : "border-blue-300 bg-blue-50 text-blue-950",
        exam.proposed && "border-dashed",
      )}
    >
      <div className="font-mono font-semibold">{exam.crn}</div>
      <div className="truncate">{exam.course_code}</div>
      <div
        className={cn("truncate font-mono", !red && "text-muted-foreground")}
      >
        {examRoom && onRoomClick ? (
          <Pivot
            label={`Explore room ${examRoom}`}
            onClick={() => onRoomClick(examRoom)}
          >
            {room}
          </Pivot>
        ) : (
          room
        )}
      </div>
      {exam.proposed && <div className="italic">Proposed</div>}
    </div>
  );
}
