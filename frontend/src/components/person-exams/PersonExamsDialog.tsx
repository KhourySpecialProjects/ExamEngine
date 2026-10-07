import { Compass, Loader2 } from "lucide-react";
import Link from "next/link";
import { CopyButton } from "@/components/common/CopyButton";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { PersonExam, PersonKind } from "@/lib/api/schedules";
import { usePersonExams } from "@/lib/hooks/usePersonExams";
import { scheduleHref } from "@/lib/scheduleView";
import { useExplorePeopleStore } from "@/lib/store/explorePeopleStore";
import { PersonExams } from "./PersonExams";

/** How an ID of each kind is named in labels: "NUId 001234567", "instructor I-1". */
export const PERSON_ID_LABEL: Record<PersonKind, string> = {
  student: "NUId",
  instructor: "instructor",
};

/**
 * Loads one person's exams in a schedule and shows them (list + exam week).
 * "Open in Explore" switches the schedule page to Explore with this person;
 * it is left out with a proposed late add, which only this dialog can draw.
 */
export function PersonExamsDialog({
  scheduleId,
  kind,
  personId,
  proposed,
  onClose,
}: {
  scheduleId: string;
  kind: PersonKind;
  personId: string;
  /** A late-add candidate to draw with the person's exams. */
  proposed?: PersonExam | null;
  onClose: () => void;
}) {
  const pickPerson = useExplorePeopleStore((state) => state.pick);
  const { result, error, isLoading } = usePersonExams(
    scheduleId,
    kind,
    personId,
  );
  const idLabel = `${PERSON_ID_LABEL[kind]} ${personId}`;

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-1.5">
            Exams for {idLabel}
            <CopyButton value={personId} label={`Copy ${idLabel}`} />
          </DialogTitle>
          <DialogDescription>
            {proposed
              ? `In this schedule, plus the proposed late add CRN ${proposed.crn} (dashed).`
              : "In this schedule. Unscheduled exams are listed last."}
          </DialogDescription>
          {!proposed && (
            <Button asChild variant="link" className="h-auto self-start p-0">
              <Link
                href={scheduleHref(scheduleId, { view: "explore", kind })}
                onClick={() => {
                  // The ID goes to sessionStorage, not the URL.
                  pickPerson(scheduleId, kind, personId);
                  onClose();
                }}
              >
                <Compass className="size-4" aria-hidden />
                Open in Explore
              </Link>
            </Button>
          )}
        </DialogHeader>
        <div className="max-h-[65vh] overflow-y-auto pr-1">
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
          {result && <PersonExams result={result} proposed={proposed} />}
        </div>
      </DialogContent>
    </Dialog>
  );
}
