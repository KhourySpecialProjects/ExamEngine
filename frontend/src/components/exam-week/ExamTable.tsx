import type { ReactNode } from "react";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { slotOf, type WeekExam } from "./examWeek";
import { Pivot } from "./Pivot";

export type ExamColumn =
  | "day"
  | "time"
  | "crn"
  | "course"
  | "room"
  | "instructor"
  | "size";

const HEADERS: Record<ExamColumn, string> = {
  day: "Day",
  time: "Time",
  crn: "CRN",
  course: "Course",
  room: "Room",
  instructor: "Instructor",
  size: "Size",
};

/**
 * Exams as a table in the given order. `doubleBooked` and `blocked` slot keys
 * get a "Double-booked" / "Blocked slot" badge. With `onInstructorClick` and
 * `onRoomClick` an instructor ID and a room are links.
 */
export function ExamTable({
  exams,
  columns = ["day", "time", "crn", "course", "room"],
  doubleBooked,
  blocked,
  onInstructorClick,
  onRoomClick,
  className,
}: {
  exams: WeekExam[];
  columns?: ExamColumn[];
  doubleBooked?: ReadonlySet<string>;
  blocked?: ReadonlySet<string>;
  onInstructorClick?: (instructorId: string) => void;
  onRoomClick?: (room: string) => void;
  className?: string;
}) {
  const cell = (exam: WeekExam, column: ExamColumn): ReactNode => {
    const slot = slotOf(exam);
    switch (column) {
      case "day":
        return (
          <TableCell
            key={column}
            className={cn(!slot && "text-muted-foreground")}
          >
            {exam.day_name ?? "Unscheduled"}
          </TableCell>
        );
      case "time":
        return (
          <TableCell key={column}>
            <span className="inline-flex items-center gap-1.5">
              {exam.block_time ?? "—"}
              {slot && doubleBooked?.has(slot) && (
                <Badge variant="destructive">Double-booked</Badge>
              )}
              {slot && blocked?.has(slot) && (
                <Badge variant="destructive">Blocked slot</Badge>
              )}
            </span>
          </TableCell>
        );
      case "crn":
        return (
          <TableCell key={column}>
            <span className="inline-flex items-center gap-1.5 font-mono">
              {exam.crn}
              {exam.proposed && (
                <Badge variant="outline" className="border-dashed font-sans">
                  Proposed
                </Badge>
              )}
            </span>
          </TableCell>
        );
      case "course":
        return <TableCell key={column}>{exam.course_code}</TableCell>;
      case "room": {
        const room = exam.room;
        return (
          <TableCell
            key={column}
            className={cn("font-mono", !room && "text-muted-foreground")}
          >
            {room && onRoomClick ? (
              <Pivot
                label={`Explore room ${room}`}
                onClick={() => onRoomClick(room)}
              >
                {room}
              </Pivot>
            ) : (
              (room ?? (slot ? "No room" : "—"))
            )}
          </TableCell>
        );
      }
      case "instructor": {
        const id = exam.instructor;
        return (
          <TableCell
            key={column}
            className={cn("font-mono", !id && "text-muted-foreground")}
          >
            {id && onInstructorClick ? (
              <Pivot
                label={`Explore instructor ${id}`}
                onClick={() => onInstructorClick(id)}
              >
                {id}
              </Pivot>
            ) : (
              (id ?? "—")
            )}
          </TableCell>
        );
      }
      case "size":
        return (
          <TableCell key={column} className="tabular-nums">
            {exam.size ?? "—"}
          </TableCell>
        );
    }
  };

  return (
    <div className={cn("rounded-md border", className)}>
      <Table aria-label="Exams" className="[&_td]:py-1 [&_th]:h-8">
        <TableHeader className="sticky top-0 bg-background">
          <TableRow>
            {columns.map((column) => (
              <TableHead key={column}>{HEADERS[column]}</TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {exams.map((exam) => (
            <TableRow key={`${exam.crn}-${exam.proposed ? "proposed" : ""}`}>
              {columns.map((column) => cell(exam, column))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
