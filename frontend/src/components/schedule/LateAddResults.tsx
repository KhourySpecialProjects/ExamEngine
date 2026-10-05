"use client";

import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Info,
  XCircle,
} from "lucide-react";
import { useState } from "react";
import { CopyButton } from "@/components/common/CopyButton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type {
  LateAddCandidate,
  LateAddConflictCounts,
  LateAddExam,
  LateAddRoom,
  LateAddSearchResult,
} from "@/lib/api/schedules";
import { cn } from "@/lib/utils";

type Outcome = LateAddSearchResult["outcome"];

/** Same colours as the Validate dialog: pass green, warn amber, fail red. */
const OUTCOMES: Record<
  Outcome,
  { icon: typeof Info; className: string; title: string }
> = {
  clear: {
    icon: CheckCircle2,
    className: "text-green-600",
    title: "Clear blocks found",
  },
  least_conflicts: {
    icon: AlertTriangle,
    className: "text-amber-600",
    title: "No clear block, fewest conflicts first",
  },
  no_room: {
    icon: XCircle,
    className: "text-red-600",
    title: "No block has a free room that fits",
  },
};

/** Identifies a candidate: a block is listed at most once. */
export function slotKey(slot: { day: number; block: number }): string {
  return `${slot.day}-${slot.block}`;
}

function plural(count: number, noun: string): string {
  return `${count} ${noun}${count === 1 ? "" : "s"}`;
}

function roomText(room: LateAddRoom): string {
  return `${room.name} (capacity ${room.capacity})`;
}

function slotText(exam: LateAddExam): string {
  return exam.day_name && exam.block_time
    ? `${exam.day_name} ${exam.block_time}`
    : "unscheduled";
}

/** Block index -> time, from every block the response names. */
function blockTimes(result: LateAddSearchResult): Map<number, string> {
  const times = new Map<number, string>();
  for (const slot of [
    ...result.candidates,
    ...result.no_room_blocks,
    ...result.instructor_exams,
    ...result.sibling_sections,
  ]) {
    if (slot.block !== null && slot.block_time) {
      times.set(slot.block, slot.block_time);
    }
  }
  return times;
}

interface Person {
  id: string;
  detail: string;
}

interface ConflictItem {
  key: keyof LateAddConflictCounts;
  label: string;
  count: number;
  /** Shown as "N students"; instructor and course items are 0/1. */
  countsStudents: boolean;
  /** Student or instructor conflict (not back-to-back or large course late). */
  hard: boolean;
  people: Person[];
}

function conflictItems(
  candidate: LateAddCandidate,
  instructorId: string,
  blockLabel: (blocks: number[]) => string,
): ConflictItem[] {
  const { conflicts: c, students, instructor } = candidate;
  const items: ConflictItem[] = [
    {
      key: "student_double_book",
      label: "Student double-book",
      count: c.student_double_book,
      countsStudents: true,
      hard: true,
      people: students.double_book.map((s) => ({
        id: s.student_id,
        detail: `also in CRN ${s.crns.join(", ")}`,
      })),
    },
    {
      key: "student_over_daily_limit",
      label: "Student per-day limit",
      count: c.student_over_daily_limit,
      countsStudents: true,
      hard: true,
      people: students.over_daily_limit.map((s) => ({
        id: s.student_id,
        detail: `${plural(s.exams, "exam")} that day`,
      })),
    },
    {
      key: "instructor_double_book",
      label: "Instructor double-book",
      count: c.instructor_double_book,
      countsStudents: false,
      hard: true,
      people: [
        {
          id: instructorId,
          detail: `also teaches CRN ${instructor.double_book_crns.join(", ")}`,
        },
      ],
    },
    {
      key: "instructor_over_daily_limit",
      label: "Instructor per-day limit",
      count: c.instructor_over_daily_limit,
      countsStudents: false,
      hard: true,
      people: [
        {
          id: instructorId,
          detail: `${plural(instructor.exams_that_day, "exam")} that day`,
        },
      ],
    },
    {
      key: "back_to_back_students",
      label: "Student back-to-back",
      count: c.back_to_back_students,
      countsStudents: true,
      hard: false,
      people: students.back_to_back.map((s) => ({
        id: s.student_id,
        detail: blockLabel(s.blocks),
      })),
    },
    {
      key: "back_to_back_instructor",
      label: "Instructor back-to-back",
      count: c.back_to_back_instructor,
      countsStudents: false,
      hard: false,
      people: [{ id: instructorId, detail: blockLabel(instructor.day_blocks) }],
    },
    {
      key: "large_course_late",
      label: "Large course in a late block",
      count: c.large_course_late,
      countsStudents: false,
      hard: false,
      people: [],
    },
  ];
  return items.filter((item) => item.count > 0);
}

export interface LateAddResultsProps {
  result: LateAddSearchResult;
  /** `slotKey` of the chosen candidate. */
  selectedSlot: string | null;
  /** Room picked per candidate (`slotKey`); absent = the best-fit room. */
  rooms: Record<string, string>;
  onSelect: (slot: string) => void;
  onRoomChange: (slot: string, room: string) => void;
}

/** A finished late-add search: outcome, context lines and the ranked blocks. */
export function LateAddResults({
  result,
  selectedSlot,
  rooms,
  onSelect,
  onRoomChange,
}: LateAddResultsProps) {
  const outcome = OUTCOMES[result.outcome];
  const Icon = outcome.icon;
  const times = blockTimes(result);
  const blockLabel = (blocks: number[]) =>
    blocks.map((b) => times.get(b) ?? `block ${b + 1}`).join(", ");
  const exams = result.instructor_exams.length;

  return (
    <div className="space-y-4">
      <div className="space-y-1">
        <h3
          className={cn(
            "flex items-center gap-2 text-sm font-semibold",
            outcome.className,
          )}
        >
          <Icon className="h-4 w-4 shrink-0" />
          {outcome.title}
        </h3>
        <p className="text-sm text-muted-foreground">
          CRN {result.crn} · {result.course_code} ·{" "}
          {plural(result.size, "student")}
        </p>
        <p className="text-sm">
          {exams === 0
            ? "No exams for this instructor in this schedule"
            : `${plural(exams, "exam")} for this instructor in this schedule`}
        </p>
        {result.sibling_sections.length > 0 && (
          <p className="text-sm">
            Other sections of {result.course_code}:{" "}
            {result.sibling_sections
              .map((exam) => `CRN ${exam.crn} (${slotText(exam)})`)
              .join(", ")}
          </p>
        )}
        {result.notes.length > 0 && (
          <ul className="space-y-0.5 text-sm text-muted-foreground">
            {result.notes.map((note) => (
              <li key={note} className="flex gap-1.5">
                <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                {note}
              </li>
            ))}
          </ul>
        )}
      </div>

      {result.outcome === "no_room" ? (
        <NoRoomBlocks result={result} />
      ) : (
        <ol className="space-y-2" aria-label="Blocks, best first">
          {result.candidates.map((candidate, index) => {
            const slot = slotKey(candidate);
            return (
              <CandidateRow
                key={slot}
                rank={index + 1}
                candidate={candidate}
                items={conflictItems(
                  candidate,
                  result.instructor_id,
                  blockLabel,
                )}
                warning={result.outcome === "least_conflicts"}
                selected={selectedSlot === slot}
                room={rooms[slot] ?? candidate.room.name}
                onSelect={() => onSelect(slot)}
                onRoomChange={(room) => {
                  onRoomChange(slot, room);
                  onSelect(slot);
                }}
              />
            );
          })}
        </ol>
      )}
    </div>
  );
}

function NoRoomBlocks({ result }: { result: LateAddSearchResult }) {
  return (
    <section className="space-y-1">
      <h4 className="text-sm font-medium">Largest free room per block</h4>
      <ul className="grid gap-x-6 gap-y-0.5 text-sm md:grid-cols-2">
        {result.no_room_blocks.map((block) => (
          <li key={slotKey(block)}>
            {block.day_name} {block.block_time}:{" "}
            <span className="text-muted-foreground">
              {block.largest_free_room
                ? roomText(block.largest_free_room)
                : "no free room"}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function CandidateRow({
  rank,
  candidate,
  items,
  warning,
  selected,
  room,
  onSelect,
  onRoomChange,
}: {
  rank: number;
  candidate: LateAddCandidate;
  items: ConflictItem[];
  warning: boolean;
  selected: boolean;
  room: string;
  onSelect: () => void;
  onRoomChange: (room: string) => void;
}) {
  const when = `${candidate.day_name} ${candidate.block_time}`;
  return (
    <li
      data-testid={`candidate-${slotKey(candidate)}`}
      data-selected={selected}
      className={cn(
        "space-y-2 rounded-md border p-3",
        selected && "border-primary ring-1 ring-primary",
      )}
    >
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <label className="flex cursor-pointer items-center gap-2 text-sm font-medium">
          <input
            type="radio"
            name="late-add-block"
            checked={selected}
            onChange={onSelect}
            className="accent-primary"
          />
          <span className="text-muted-foreground">{rank}.</span>
          {when}
        </label>
        <RoomPicker
          when={when}
          candidate={candidate}
          value={room}
          onChange={onRoomChange}
        />
      </div>
      {items.length === 0 ? (
        <p className="text-xs text-muted-foreground">No conflicts</p>
      ) : (
        <ul className="space-y-1">
          {items.map((item) => (
            <ConflictRow key={item.key} item={item} warning={warning} />
          ))}
        </ul>
      )}
    </li>
  );
}

function RoomPicker({
  when,
  candidate,
  value,
  onChange,
}: {
  when: string;
  candidate: LateAddCandidate;
  value: string;
  onChange: (room: string) => void;
}) {
  if (candidate.other_rooms.length === 0) {
    return (
      <span className="text-sm text-muted-foreground">
        {roomText(candidate.room)}
      </span>
    );
  }
  const options = [candidate.room, ...candidate.other_rooms];
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger size="sm" aria-label={`Room for ${when}`}>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {options.map((option, index) => (
          <SelectItem key={option.name} value={option.name}>
            {roomText(option)}
            {index === 0 && " · best fit"}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

function ConflictRow({
  item,
  warning,
}: {
  item: ConflictItem;
  warning: boolean;
}) {
  const [open, setOpen] = useState(false);
  const text = item.countsStudents
    ? `${item.label}: ${plural(item.count, "student")}`
    : item.label;
  const className = cn(
    "text-xs",
    warning && item.hard ? "text-amber-600" : "text-muted-foreground",
  );
  if (item.people.length === 0) return <li className={className}>{text}</li>;

  const Chevron = open ? ChevronDown : ChevronRight;
  return (
    <li className={className}>
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1 rounded-sm hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <Chevron className="h-3 w-3" />
        {text}
      </button>
      {open && (
        <div className="mt-1 space-y-1 pl-4 text-foreground">
          {item.people.length > 1 && (
            <div className="flex items-center gap-1 text-muted-foreground">
              Copy all
              <CopyButton
                value={item.people.map((p) => p.id).join("\n")}
                label={`Copy all IDs: ${item.label}`}
              />
            </div>
          )}
          <ul className="max-h-40 space-y-0.5 overflow-y-auto">
            {item.people.map((person) => (
              <li key={person.id} className="flex items-center gap-1.5">
                <span className="font-mono">{person.id}</span>
                <CopyButton value={person.id} label={`Copy ${person.id}`} />
                <span className="text-muted-foreground">{person.detail}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </li>
  );
}
