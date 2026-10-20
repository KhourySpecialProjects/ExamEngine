"use client";

import { Loader2, Save } from "lucide-react";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type {
  LateAddCandidate,
  LateAddConflictCounts,
  LateAddSearchResult,
} from "@/lib/api/schedules";
import { useSchedulesStore } from "@/lib/store/schedulesStore";
import { plural, slotKey } from "./LateAddResults";

/** The server's limit on schedule names. */
const MAX_NAME_LENGTH = 50;

/** "<base> + <CRN>", the base shortened so the CRN always fits. */
function defaultName(scheduleName: string, crn: string): string {
  const suffix = ` + ${crn}`;
  const base = scheduleName
    .slice(0, Math.max(0, MAX_NAME_LENGTH - suffix.length))
    .trimEnd();
  return `${base}${suffix}`.trim().slice(0, MAX_NAME_LENGTH);
}

/** A placement's conflict counts, e.g. "2 students double-booked, instructor back-to-back". */
export function conflictSummary(c: LateAddConflictCounts): string {
  const parts: string[] = [];
  if (c.student_double_book > 0) {
    parts.push(`${plural(c.student_double_book, "student")} double-booked`);
  }
  if (c.student_over_daily_limit > 0) {
    parts.push(
      `${plural(c.student_over_daily_limit, "student")} over the daily limit`,
    );
  }
  if (c.instructor_double_book > 0) parts.push("instructor double-booked");
  if (c.instructor_over_daily_limit > 0) {
    parts.push("instructor over the daily limit");
  }
  if (c.back_to_back_students > 0) {
    parts.push(`${plural(c.back_to_back_students, "student")} back-to-back`);
  }
  if (c.back_to_back_instructor > 0) parts.push("instructor back-to-back");
  if (c.large_course_late > 0) parts.push("large course in a late block");
  return parts.join(", ");
}

export interface LateAddSaveFormProps {
  scheduleId: string;
  scheduleName: string;
  result: LateAddSearchResult;
  /** The chosen block. */
  candidate: LateAddCandidate;
  /** The chosen room in that block. */
  room: string;
  /** Closes the dialog: called before leaving for another schedule. */
  onLeave: () => void;
}

/** Saves the chosen placement as a new schedule and opens it. */
export function LateAddSaveForm({
  scheduleId,
  scheduleName,
  result,
  candidate,
  room,
  onLeave,
}: LateAddSaveFormProps) {
  const router = useRouter();
  const lateAddSave = useSchedulesStore((state) => state.lateAddSave);
  const [name, setName] = useState(() => defaultName(scheduleName, result.crn));
  // The accepted block: choosing another one needs a new confirmation.
  const [acceptedSlot, setAcceptedSlot] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  // The save error, tied to the placement it was raised for.
  const [failure, setFailure] = useState<{
    placement: string;
    message: string;
  } | null>(null);

  const slot = slotKey(candidate);
  const placement = `${slot}|${room}`;
  // Another block or room: the error was about the old one, so drop it.
  if (failure !== null && failure.placement !== placement) setFailure(null);
  const error = failure?.placement === placement ? failure.message : null;
  const needsConfirmation = result.outcome === "least_conflicts";
  const accepted = acceptedSlot === slot;

  const handleSave = async (event: FormEvent) => {
    event.preventDefault();
    setIsSaving(true);
    setFailure(null);
    try {
      const saved = await lateAddSave(scheduleId, {
        crn: result.crn,
        course_code: result.course_code,
        instructor_id: result.instructor_id,
        day: candidate.day,
        block: candidate.block,
        room,
        schedule_name: name.trim(),
        accept_conflicts: needsConfirmation && accepted,
      });
      toast.success(`Saved ${saved.schedule_name}`);
      onLeave();
      router.push(`/dashboard/${saved.schedule_id}`);
    } catch (err) {
      setFailure({
        placement,
        message: err instanceof Error ? err.message : "Unknown error",
      });
      setIsSaving(false);
    }
  };

  return (
    <form
      onSubmit={handleSave}
      aria-label="Save as new schedule"
      className="space-y-3 border-t pt-4"
    >
      <p className="text-sm">
        Saves a new schedule with CRN {result.crn} on {candidate.day_name}{" "}
        {candidate.block_time} in {room}. This schedule is not changed.
      </p>

      <div className="space-y-1">
        <Label htmlFor="late-add-schedule-name">New schedule name</Label>
        <Input
          id="late-add-schedule-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={MAX_NAME_LENGTH}
          autoComplete="off"
          className="max-w-md"
        />
      </div>

      {needsConfirmation && (
        <div className="flex items-start gap-2">
          <Checkbox
            id="late-add-accept-conflicts"
            checked={accepted}
            onCheckedChange={(checked) =>
              setAcceptedSlot(checked === true ? slot : null)
            }
            className="mt-0.5"
          />
          <Label
            htmlFor="late-add-accept-conflicts"
            className="text-sm font-normal leading-snug"
          >
            Save with these conflicts: {conflictSummary(candidate.conflicts)}
          </Label>
        </div>
      )}

      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}

      <Button
        type="submit"
        disabled={!name.trim() || isSaving || (needsConfirmation && !accepted)}
      >
        {isSaving ? (
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        ) : (
          <Save className="mr-2 h-4 w-4" />
        )}
        {isSaving ? "Saving…" : "Save as new schedule"}
      </Button>
    </form>
  );
}
