import { Check, Copy } from "lucide-react";
import { CopyButton, useCopy } from "@/components/common/CopyButton";
import { PersonIdActions } from "@/components/person-exams/PersonIdActions";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { conflictTypeMap, conflictTypeRank } from "@/lib/hooks/useConflictData";
import {
  type ConflictCourse,
  type ConflictDataByType,
  type ConflictType,
  isBackToBackConflictType,
  isInstructorConflictType,
  isPerDayLimitConflictType,
  isPersonConflictType,
  summarizeConflictsByCourse,
} from "@/lib/hooks/useConflictDataSimple";

/** Block as shown to users: "0 (9AM-11AM)" → "9AM-11AM", "2" → "Block 2". */
function blockTime(block: string): string {
  const inParens = /\(([^)]+)\)/.exec(block)?.[1];
  if (inParens) return inParens;
  return /^\d+$/.test(block.trim()) ? `Block ${block.trim()}` : block;
}

function CopyAllButton({ people }: { people: string[] }) {
  const { copied, copy } = useCopy();
  const Icon = copied ? Check : Copy;
  return (
    <Button
      variant="outline"
      size="sm"
      onClick={() => void copy(people.join("\n"))}
    >
      <Icon aria-hidden />
      Copy all
    </Button>
  );
}

function TypeSection({
  type,
  course,
  rowsByType,
  scheduleId,
}: {
  type: ConflictType;
  course: ConflictCourse;
  rowsByType: ConflictDataByType;
  scheduleId: string | undefined;
}) {
  const label = conflictTypeMap[type] ?? type;
  const isInstructor = isInstructorConflictType(type);
  const noun = isInstructor ? "instructor" : "student";

  if (isBackToBackConflictType(type)) {
    return (
      <section aria-label={label} className="space-y-1">
        <h3 className="text-sm font-semibold">{label}: n/a</h3>
        <p className="text-sm text-muted-foreground">
          Back-to-back conflicts don't record which exams are involved yet.
        </p>
      </section>
    );
  }

  const summary = summarizeConflictsByCourse(rowsByType[type] ?? []).find(
    (s) =>
      course.crn ? s.crn === course.crn : !s.crn && s.course === course.course,
  );
  const people = summary?.people ?? [];
  const named = people.filter(Boolean);

  return (
    <section aria-label={label} className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold">
          {label}: {people.length} {noun}
          {people.length === 1 ? "" : "s"}
        </h3>
        {named.length > 0 && <CopyAllButton people={named} />}
      </div>
      {isPerDayLimitConflictType(type) && people.length > 0 && (
        <p className="text-xs text-muted-foreground">
          Only people for whom this exam went over the daily limit.
        </p>
      )}
      {people.length > 0 && (
        <ul className="grid max-h-40 grid-cols-2 gap-x-4 gap-y-1 overflow-y-auto text-sm sm:grid-cols-3">
          {people.map((person, i) => (
            <li
              // Several people can lack an ID; position keeps keys unique.
              key={`${i}-${person}`}
              className="flex items-center gap-1 tabular-nums"
            >
              <span className="truncate">{person || "—"}</span>
              {person && (
                <PersonIdActions
                  id={person}
                  kind={isInstructor ? "instructor" : "student"}
                  scheduleId={scheduleId}
                />
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/**
 * Everyone whose conflicts involve one course (CRN), per conflict type.
 * Built from the same per-course aggregation as the "By course" view.
 */
export function CourseConflictDialog({
  course,
  rowsByType,
  scheduleId,
  onClose,
}: {
  course: ConflictCourse | null;
  rowsByType: ConflictDataByType;
  /** The schedule the people's exams are looked up in. */
  scheduleId: string | undefined;
  onClose: () => void;
}) {
  const types = Object.keys(rowsByType)
    .filter(isPersonConflictType)
    .sort((a, b) => conflictTypeRank(a) - conflictTypeRank(b));
  const exam = course?.exam;
  const details = exam
    ? [
        `${exam.Day} ${blockTime(exam.Block)}`,
        exam.Room,
        `${exam.Size} enrolled`,
      ].filter(Boolean)
    : [];

  return (
    <Dialog open={course != null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-2xl">
        {course && (
          <>
            <DialogHeader>
              <DialogTitle>{course.course || `CRN ${course.crn}`}</DialogTitle>
              <DialogDescription asChild>
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                  {course.crn && (
                    <span className="inline-flex items-center gap-1 tabular-nums">
                      CRN {course.crn}
                      <CopyButton
                        value={course.crn}
                        label={`Copy CRN ${course.crn}`}
                      />
                    </span>
                  )}
                  {details.map((d) => (
                    <span key={d}>{d}</span>
                  ))}
                </div>
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              {types.map((type) => (
                <TypeSection
                  key={type}
                  type={type}
                  course={course}
                  rowsByType={rowsByType}
                  scheduleId={scheduleId}
                />
              ))}
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
