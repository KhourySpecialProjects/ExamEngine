import { Ban, GitMerge } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { examsBySlot, slotKey, type WeekExam } from "./examWeek";
import { CombinedMark, CommonBadge } from "./GroupMarks";
import { Pivot } from "./Pivot";

/** Diagonal orange stripes: the look of a blocked slot (also in the legend). */
export const BLOCKED_SLOT_CLASS =
  "bg-[repeating-linear-gradient(135deg,var(--color-orange-100)_0_6px,var(--color-orange-50)_6px_12px)]";

const BLOCK_CLASS = "rounded border px-1.5 py-1 leading-tight";
const NORMAL_CLASS = "border-blue-300 bg-blue-50 text-blue-950";
const RED_CLASS = "border-destructive bg-destructive/10 text-destructive";

/** A slot's exams with the sections of one combined group drawn together. */
type CellItem =
  | { kind: "exam"; exam: WeekExam }
  | { kind: "combined"; label: string; exams: WeekExam[] };

function cellItems(exams: WeekExam[]): CellItem[] {
  const count = new Map<string, number>();
  for (const exam of exams) {
    if (exam.combined)
      count.set(exam.combined, (count.get(exam.combined) ?? 0) + 1);
  }
  const items: CellItem[] = [];
  const frames = new Map<string, WeekExam[]>();
  for (const exam of exams) {
    const label = exam.combined;
    if (!label || (count.get(label) ?? 0) < 2) {
      items.push({ kind: "exam", exam });
      continue;
    }
    const frame = frames.get(label);
    if (frame) {
      frame.push(exam);
    } else {
      const members = [exam];
      frames.set(label, members);
      items.push({ kind: "combined", label, exams: members });
    }
  }
  return items;
}

/**
 * The schedule's exam week (days across, blocks down) with each scheduled
 * exam blocked out; unscheduled exams are left out. Two or more sections of
 * one combined exam in a block are one framed block. Blocks in a
 * `doubleBooked` slot are red. `blocked` slots are striped orange, and an
 * exam inside one is red. A common exam has a violet badge; with
 * `commonSections` it opens the group's sections. With `onRoomClick` rooms
 * are links.
 */
export function ExamWeekGrid({
  days,
  blockTimes,
  exams,
  doubleBooked,
  blocked,
  onRoomClick,
  commonSections,
}: {
  days: string[];
  blockTimes: string[];
  exams: WeekExam[];
  doubleBooked?: ReadonlySet<string>;
  blocked?: ReadonlySet<string>;
  onRoomClick?: (room: string) => void;
  /** Every section of a common group, for its badge's list. */
  commonSections?: (label: string) => WeekExam[];
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
                const isBlocked = !!blocked?.has(key);
                const red = !!doubleBooked?.has(key) || isBlocked;
                const notes = [
                  doubleBooked?.has(key) && "double-booked",
                  isBlocked && "in a blocked slot",
                ].filter((note): note is string => !!note);
                const marks = (exam: WeekExam) => {
                  const label = exam.common;
                  return (
                    label && (
                      <CommonBadge
                        label={label}
                        sections={
                          commonSections && (() => commonSections(label))
                        }
                        onRoomClick={onRoomClick}
                      />
                    )
                  );
                };
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
                      {cellItems(perSlot.get(key) ?? []).map((item) =>
                        item.kind === "combined" ? (
                          <CombinedFrame
                            key={`combined-${item.label}`}
                            label={item.label}
                            exams={item.exams}
                            red={red}
                            notes={notes}
                            marks={marks(item.exams[0])}
                            onRoomClick={onRoomClick}
                          />
                        ) : (
                          <ExamBlock
                            key={`${item.exam.crn}-${item.exam.proposed ? "proposed" : ""}`}
                            exam={item.exam}
                            red={red}
                            notes={notes}
                            marks={marks(item.exam)}
                            onRoomClick={onRoomClick}
                          />
                        ),
                      )}
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

function RoomText({
  room,
  red,
  onRoomClick,
}: {
  room: string | null;
  red: boolean;
  onRoomClick?: (room: string) => void;
}) {
  return (
    <span className={cn("font-mono", !red && "text-muted-foreground")}>
      {room && onRoomClick ? (
        <Pivot label={`Explore room ${room}`} onClick={() => onRoomClick(room)}>
          {room}
        </Pivot>
      ) : (
        (room ?? "No room")
      )}
    </span>
  );
}

function ExamBlock({
  exam,
  red,
  notes,
  marks,
  onRoomClick,
}: {
  exam: WeekExam;
  red: boolean;
  notes: string[];
  marks: ReactNode;
  onRoomClick?: (room: string) => void;
}) {
  const title = [
    `CRN ${exam.crn} · ${exam.course_code}`,
    `Room: ${exam.room ?? "No room"}`,
    exam.combined && `Combined exam: ${exam.combined}`,
    exam.common && `Common exam: ${exam.common}`,
    exam.proposed && "proposed late add",
    ...notes,
  ].filter(Boolean);
  return (
    <div
      title={title.join("\n")}
      className={cn(
        BLOCK_CLASS,
        red ? RED_CLASS : NORMAL_CLASS,
        exam.proposed && "border-dashed",
      )}
    >
      <div className="flex items-center gap-1">
        <span className="font-mono font-semibold">{exam.crn}</span>
        {exam.combined && <CombinedMark label={exam.combined} />}
        {marks}
      </div>
      <div className="truncate">{exam.course_code}</div>
      <div className="truncate">
        <RoomText room={exam.room} red={red} onRoomClick={onRoomClick} />
      </div>
      {exam.proposed && <div className="italic">Proposed</div>}
    </div>
  );
}

/** Sections of one combined exam in one block: one exam in one room. */
function CombinedFrame({
  label,
  exams,
  red,
  notes,
  marks,
  onRoomClick,
}: {
  label: string;
  exams: WeekExam[];
  red: boolean;
  notes: string[];
  marks: ReactNode;
  onRoomClick?: (room: string) => void;
}) {
  const sizes = exams.map((exam) => exam.size);
  const total = sizes.every((size) => size != null)
    ? sizes.reduce<number>((sum, size) => sum + (size ?? 0), 0)
    : null;
  const room = exams[0].room;
  return (
    <div
      data-testid="combined-exam"
      title={[`Combined exam: ${label}`, ...notes].join("\n")}
      className={cn(
        BLOCK_CLASS,
        "border-2",
        red ? RED_CLASS : "border-blue-400 bg-blue-50 text-blue-950",
      )}
    >
      <div className="flex items-center gap-1 font-semibold">
        <GitMerge className="size-3 shrink-0" aria-hidden />
        <span className="truncate">{label}</span>
        {marks}
      </div>
      <div className="truncate">
        <RoomText room={room} red={red} onRoomClick={onRoomClick} />
        {total != null && (
          <span className={cn(!red && "text-muted-foreground")}>
            {" "}
            · {total} students
          </span>
        )}
      </div>
      <ul className="mt-0.5 space-y-0.5 border-t border-current/20 pt-0.5">
        {exams.map((exam) => (
          <li key={exam.crn} className="truncate">
            <span className="font-mono font-semibold">{exam.crn}</span>{" "}
            {exam.course_code}
          </li>
        ))}
      </ul>
    </div>
  );
}
