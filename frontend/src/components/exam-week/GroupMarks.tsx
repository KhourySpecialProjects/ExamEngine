import { GitMerge, Layers } from "lucide-react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import type { WeekExam } from "./examWeek";
import { Pivot } from "./Pivot";

/** The List view's Combined icon (blue merge). */
export function CombinedMark({ label }: { label: string }) {
  return (
    <GitMerge
      className="size-3 shrink-0 text-blue-700"
      aria-label={`Combined exam ${label}`}
    />
  );
}

const COMMON_BADGE_CLASS =
  "inline-flex shrink-0 items-center rounded border border-violet-300 bg-violet-50 px-0.5 text-violet-700";

/**
 * The List view's Common badge (violet layers). With `sections` it opens a
 * list of the common exam's sections and their rooms; with `onRoomClick` each
 * room is a link.
 */
export function CommonBadge({
  label,
  sections,
  onRoomClick,
}: {
  label: string;
  sections?: () => WeekExam[];
  onRoomClick?: (room: string) => void;
}) {
  const name = `Common exam ${label}`;
  if (!sections) {
    return (
      <span className={COMMON_BADGE_CLASS} title={name}>
        <Layers className="size-3" aria-hidden />
        <span className="sr-only">{name}</span>
      </span>
    );
  }
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          aria-label={`${name}: show its sections`}
          title={name}
          className={cn(
            COMMON_BADGE_CLASS,
            "cursor-pointer hover:bg-violet-100",
          )}
        >
          <Layers className="size-3" aria-hidden />
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-80 text-xs" align="start">
        <CommonSections
          label={label}
          sections={sections()}
          onRoomClick={onRoomClick}
        />
      </PopoverContent>
    </Popover>
  );
}

function CommonSections({
  label,
  sections,
  onRoomClick,
}: {
  label: string;
  sections: WeekExam[];
  onRoomClick?: (room: string) => void;
}) {
  const rooms = new Set(sections.map((s) => s.room).filter(Boolean)).size;
  return (
    <div className="space-y-2">
      <div>
        <div className="flex items-center gap-1.5 font-semibold text-violet-800">
          <Layers className="size-3.5" aria-hidden />
          {label}
        </div>
        <div className="text-muted-foreground">
          Common exam: {sections.length} section
          {sections.length === 1 ? "" : "s"} in {rooms} room
          {rooms === 1 ? "" : "s"}
          {sections[0]?.day_name &&
            `, ${sections[0].day_name} ${sections[0].block_time}`}
        </div>
      </div>
      <ul
        aria-label={`Sections of ${label}`}
        className="max-h-60 space-y-0.5 overflow-y-auto"
      >
        {sections.map(({ crn, course_code, room }) => (
          <li key={crn} className="flex items-baseline gap-2">
            <span className="font-mono font-semibold">{crn}</span>
            <span className="truncate">{course_code}</span>
            <span className="ml-auto font-mono">
              {room && onRoomClick ? (
                <Pivot
                  label={`Explore room ${room}`}
                  onClick={() => onRoomClick(room)}
                >
                  {room}
                </Pivot>
              ) : (
                (room ?? "No room")
              )}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
