import { CalendarSearch } from "lucide-react";
import { useState } from "react";
import {
  CopyButton,
  ID_ICON_BUTTON_CLASS,
} from "@/components/common/CopyButton";
import type { PersonExam, PersonKind } from "@/lib/api/schedules";
import { PERSON_ID_LABEL, PersonExamsDialog } from "./PersonExamsDialog";

/** A real ID: not blank, and not a "nan" left by an empty CSV cell (EXENG-79). */
export function isPersonId(value: string | null | undefined): value is string {
  const id = value?.trim();
  return !!id && id.toLowerCase() !== "nan";
}

/**
 * Copy and "view exams" buttons for a student NUId or instructor ID. The
 * second opens that person's exams in `scheduleId`; it is left out without a
 * schedule or for a "nan" ID. Neither click reaches a parent element.
 */
export function PersonIdActions({
  id,
  kind,
  scheduleId,
  proposed,
}: {
  id: string;
  kind: PersonKind;
  scheduleId: string | undefined;
  /** A late-add candidate to draw with the person's exams. */
  proposed?: PersonExam | null;
}) {
  const [open, setOpen] = useState(false);
  const idLabel = `${PERSON_ID_LABEL[kind]} ${id}`;
  const lookIn = isPersonId(id) ? scheduleId : undefined;
  return (
    <>
      <CopyButton value={id} label={`Copy ${idLabel}`} />
      {lookIn && (
        <button
          type="button"
          aria-label={`View exams for ${idLabel}`}
          title={`View exams for ${idLabel}`}
          onClick={(e) => {
            e.stopPropagation();
            setOpen(true);
          }}
          className={ID_ICON_BUTTON_CLASS}
        >
          <CalendarSearch className="size-3" aria-hidden />
        </button>
      )}
      {lookIn && open && (
        <PersonExamsDialog
          scheduleId={lookIn}
          kind={kind}
          personId={id}
          proposed={proposed}
          onClose={() => setOpen(false)}
        />
      )}
    </>
  );
}
