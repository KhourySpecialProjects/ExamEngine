import { Loader2 } from "lucide-react";
import { type ReactNode, useMemo } from "react";
import { byWeek } from "@/components/exam-week/examWeek";
import type { ScheduleResult, ScheduleRoomsResult } from "@/lib/api/schedules";
import type { ScheduleRoomsState } from "@/lib/hooks/useScheduleRooms";
import {
  type ExploreDisplay,
  ExploreResults,
  examCount,
} from "./ExploreResults";
import { LookupCombobox } from "./LookupCombobox";
import { weekExam } from "./scheduleRows";

/**
 * Explore a room: pick it from every room of the dataset, then see its exams
 * and blocked times. The room is in the URL (`q`).
 */
export function RoomExplore({
  schedule,
  room,
  rooms,
  display,
  toolbar,
  onRoomChange,
  onInstructorClick,
}: {
  schedule: ScheduleResult;
  room: string | null;
  rooms: ScheduleRoomsState;
  display: ExploreDisplay;
  /** Shown at the end of the lookup row (the Calendar / List switch). */
  toolbar: ReactNode;
  onRoomChange: (room: string) => void;
  onInstructorClick: (instructorId: string) => void;
}) {
  const rows = schedule.schedule.complete;
  const options = useMemo(() => {
    const counts = new Map<string, number>();
    for (const row of rows) {
      if (row.Room) counts.set(row.Room, (counts.get(row.Room) ?? 0) + 1);
    }
    return (rooms.result?.rooms ?? []).map((r) => ({
      value: r.name,
      detail: `capacity ${r.capacity} · ${examCount(counts.get(r.name) ?? 0)}`,
    }));
  }, [rows, rooms.result]);
  const picked = rooms.result?.rooms.find((r) => r.name === room);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <LookupCombobox
          label="Room"
          options={options}
          value={room}
          onSelect={onRoomChange}
          placeholder={rooms.isLoading ? "Loading rooms…" : "Choose a room…"}
          searchPlaceholder="Search rooms..."
          emptyText="No room found."
        />
        {toolbar}
      </div>

      {rooms.isLoading && (
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading rooms…
        </p>
      )}
      {rooms.error && (
        <p role="alert" className="text-sm text-destructive">
          {rooms.error}
        </p>
      )}
      {rooms.result && !room && (
        <p className="text-sm text-muted-foreground">
          Choose a room to see its exams and blocked times in this schedule.
        </p>
      )}
      {rooms.result && room && !picked && (
        <p className="text-sm text-muted-foreground">
          No room named “{room}” in this schedule's dataset.
        </p>
      )}
      {rooms.result && picked && (
        <RoomResults
          rows={rows}
          room={picked}
          result={rooms.result}
          display={display}
          onInstructorClick={onInstructorClick}
        />
      )}
    </div>
  );
}

function RoomResults({
  rows,
  room,
  result,
  display,
  onInstructorClick,
}: {
  rows: ScheduleResult["schedule"]["complete"];
  room: ScheduleRoomsResult["rooms"][number];
  result: ScheduleRoomsResult;
  display: ExploreDisplay;
  onInstructorClick: (instructorId: string) => void;
}) {
  const exams = useMemo(
    () =>
      rows
        .filter((row) => row.Room === room.name)
        .map((row) => weekExam(row, result.days, result.block_times))
        .sort(byWeek),
    [rows, room.name, result],
  );
  return (
    <ExploreResults
      heading={
        <h3 className="flex items-baseline gap-1.5 font-semibold">
          Room <span className="font-mono">{room.name}</span>
          <span className="text-sm font-normal text-muted-foreground">
            (capacity {room.capacity})
          </span>
        </h3>
      }
      exams={exams}
      days={result.days}
      blockTimes={result.block_times}
      display={display}
      // Combined exams share a room and a block: no double-book marks.
      columns={["day", "time", "crn", "course", "instructor", "size"]}
      blockouts={{ slots: room.blocked, status: result.blockouts }}
      onInstructorClick={onInstructorClick}
      emptyText="No exams in this room in this schedule."
    />
  );
}
