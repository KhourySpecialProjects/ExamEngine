import { Loader2 } from "lucide-react";
import { type ReactNode, useEffect, useMemo, useState } from "react";
import { CopyButton } from "@/components/common/CopyButton";
import type { ExamGroups } from "@/components/exam-week/examGroups";
import { byWeek, type WeekExam } from "@/components/exam-week/examWeek";
import { PERSON_ID_LABEL } from "@/components/person-exams/PersonExamsDialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type {
  PersonKind,
  ScheduleExam,
  ScheduleResult,
} from "@/lib/api/schedules";
import { usePersonExams } from "@/lib/hooks/usePersonExams";
import { NO_PICK, useExplorePeopleStore } from "@/lib/store/explorePeopleStore";
import {
  type ExploreDisplay,
  ExploreResults,
  examCount,
} from "./ExploreResults";
import { LookupCombobox } from "./LookupCombobox";
import { instructorOf } from "./scheduleRows";

const HEADING: Record<PersonKind, string> = {
  student: "Student",
  instructor: "Instructor",
};

/** The schedule's instructor IDs (trimmed, no "nan"), each with its exam count. */
export function instructorOptions(exams: ScheduleExam[]) {
  const counts = new Map<string, number>();
  for (const exam of exams) {
    const id = instructorOf(exam);
    if (id) counts.set(id, (counts.get(id) ?? 0) + 1);
  }
  return [...counts]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([value, count]) => ({ value, detail: examCount(count) }));
}

/**
 * Explore a student (typed NUId) or an instructor (picked from the
 * schedule's): the lookup, a Recent list and the person's exams. The IDs live
 * in `explorePeopleStore`, never in the URL.
 */
export function PersonExplore({
  scheduleId,
  schedule,
  groups,
  kind,
  display,
  toolbar,
  onExplorePerson,
  onRoomClick,
}: {
  scheduleId: string;
  schedule: ScheduleResult;
  groups: ExamGroups;
  kind: PersonKind;
  display: ExploreDisplay;
  /** Shown at the end of the lookup row (the Calendar / List switch). */
  toolbar: ReactNode;
  onExplorePerson: (kind: PersonKind, id: string) => void;
  onRoomClick: (room: string) => void;
}) {
  const { current, recent } =
    useExplorePeopleStore((state) => state.people[scheduleId]?.[kind]) ??
    NO_PICK;
  const pick = (id: string) => onExplorePerson(kind, id);
  const rows = schedule.schedule.complete;
  const instructors = useMemo(() => instructorOptions(rows), [rows]);
  const { result, error, isLoading } = usePersonExams(
    scheduleId,
    kind,
    current ?? "",
  );

  // The person-exams reply has no instructor or size: take them from the
  // schedule's own rows.
  const exams: WeekExam[] = useMemo(() => {
    const byCrn = new Map(rows.map((row) => [row.CRN, row]));
    return (result?.exams ?? [])
      .map((exam) => {
        const row = byCrn.get(exam.crn);
        return {
          ...exam,
          instructor: instructorOf(row),
          size: row?.Size ?? null,
        };
      })
      .sort(byWeek);
  }, [result, rows]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-2">
          {kind === "student" ? (
            <StudentInput current={current} onPick={pick} />
          ) : (
            <LookupCombobox
              label="Instructor"
              options={instructors}
              value={current}
              onSelect={pick}
              placeholder="Choose an instructor…"
              searchPlaceholder="Search instructor IDs..."
              emptyText="No instructor found."
              limit={100}
            />
          )}
          {recent.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5 text-xs">
              <span className="text-muted-foreground">Recent:</span>
              {recent.map((id) => (
                <Button
                  key={id}
                  size="sm"
                  variant={id === current ? "secondary" : "outline"}
                  aria-pressed={id === current}
                  className="h-6 px-2 font-mono text-xs"
                  onClick={() => pick(id)}
                >
                  {id}
                </Button>
              ))}
            </div>
          )}
        </div>
        {toolbar}
      </div>

      {!current && (
        <p className="text-sm text-muted-foreground">
          {kind === "student"
            ? "Enter a student's NUId to see their exams in this schedule."
            : "Choose an instructor to see their exams in this schedule."}
        </p>
      )}
      {isLoading && (
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading exams…
        </p>
      )}
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
      {result && current && (
        <ExploreResults
          heading={
            <h3 className="flex items-center gap-1.5 font-semibold">
              {HEADING[kind]} <span className="font-mono">{current}</span>
              <CopyButton
                value={current}
                label={`Copy ${PERSON_ID_LABEL[kind]} ${current}`}
              />
            </h3>
          }
          exams={exams}
          days={result.days}
          blockTimes={result.block_times}
          display={display}
          columns={
            kind === "student"
              ? [
                  "day",
                  "time",
                  "crn",
                  "course",
                  "room",
                  "instructor",
                  "size",
                  "group",
                ]
              : ["day", "time", "crn", "course", "room", "size", "group"]
          }
          groups={groups}
          rows={rows}
          markDoubleBooks
          onInstructorClick={(id) => onExplorePerson("instructor", id)}
          onRoomClick={onRoomClick}
          emptyText={`No exams for this ${kind} in this schedule.`}
        />
      )}
    </div>
  );
}

function StudentInput({
  current,
  onPick,
}: {
  current: string | null;
  onPick: (id: string) => void;
}) {
  const [draft, setDraft] = useState(current ?? "");
  // A Recent pick or "Open in Explore" changes the current ID.
  useEffect(() => setDraft(current ?? ""), [current]);
  const id = draft.trim();
  return (
    <form
      className="flex gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        if (id) onPick(id);
      }}
    >
      <Input
        aria-label="NUId"
        placeholder="NUId, e.g. 001234567"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        className="w-56 font-mono"
        autoComplete="off"
      />
      <Button type="submit" disabled={!id}>
        Look up
      </Button>
    </form>
  );
}
