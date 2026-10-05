import { Loader2 } from "lucide-react";
import { CopyButton } from "@/components/common/CopyButton";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { PersonExam, PersonKind } from "@/lib/api/schedules";
import { usePersonExams } from "@/lib/hooks/usePersonExams";
import { PersonExams } from "./PersonExams";

/** How an ID of each kind is named in labels: "NUId 001234567", "instructor I-1". */
export const PERSON_ID_LABEL: Record<PersonKind, string> = {
  student: "NUId",
  instructor: "instructor",
};

/** Loads one person's exams in a schedule and shows them (list + exam week). */
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
