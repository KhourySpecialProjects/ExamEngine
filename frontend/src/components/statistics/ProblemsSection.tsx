import {
  AlertTriangle,
  Ban,
  Building2,
  CircleCheck,
  type LucideIcon,
  Users,
} from "lucide-react";
import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { UnscheduledGroup } from "@/lib/api/schedules";
import type { ExamIssue, ScheduleStats } from "@/lib/hooks/useScheduleStats";
import type { ConflictMetrics } from "@/lib/types/conflict.types";
import { cn } from "@/lib/utils";

const plural = (n: number, word: string) =>
  `${n.toLocaleString()} ${word}${n === 1 ? "" : "s"}`;

/** Heading prefix of an unscheduled entry, followed by its group label or CRN. */
const UNSCHEDULED_TITLES: Record<UnscheduledGroup["kind"], string> = {
  section: "Section: CRN",
  combined: "Combined exam:",
  common: "Common exam:",
};

function ProblemCard({
  title,
  icon: Icon,
  count,
  description,
  tone,
  children,
}: {
  title: string;
  icon: LucideIcon;
  /** Omitted when per-type counts can overlap (one person, two types). */
  count?: number;
  description: string;
  tone: "danger" | "warning";
  children?: ReactNode;
}) {
  return (
    <section aria-label={title}>
      <Card
        className={cn(
          "h-full gap-3",
          tone === "danger"
            ? "border-red-200 bg-red-50"
            : "border-orange-200 bg-orange-50",
        )}
      >
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm font-medium">
            <Icon
              aria-hidden
              className={cn(
                "h-4 w-4",
                tone === "danger" ? "text-red-600" : "text-orange-600",
              )}
            />
            {title}
            {count != null && (
              <span
                className={cn(
                  "ml-auto text-2xl font-bold tabular-nums",
                  tone === "danger" ? "text-red-700" : "text-orange-700",
                )}
              >
                {count.toLocaleString()}
              </span>
            )}
          </CardTitle>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
        {children && (
          <CardContent className="space-y-2">{children}</CardContent>
        )}
      </Card>
    </section>
  );
}

/** Collapsed by default so a long list never pushes the page down. */
function Collapsible({
  summary,
  children,
}: {
  summary: string;
  children: ReactNode;
}) {
  return (
    <details className="text-xs">
      <summary className="cursor-pointer font-medium">{summary}</summary>
      <div className="mt-2 max-h-48 overflow-y-auto">{children}</div>
    </details>
  );
}

function ExamList({ exams }: { exams: ExamIssue[] }) {
  return (
    <ul className="space-y-0.5 font-mono text-muted-foreground">
      {exams.map((e) => (
        <li key={e.crn}>
          {e.crn} {e.course && `· ${e.course}`} · {plural(e.size, "student")}
        </li>
      ))}
    </ul>
  );
}

/**
 * Everything wrong with the schedule, most serious first. Shows a single
 * all-clear line when there is nothing to fix.
 */
export function ProblemsSection({
  stats,
  conflicts,
  onShowConflicts,
}: {
  stats: ScheduleStats;
  conflicts: ConflictMetrics;
  onShowConflicts?: () => void;
}) {
  const { unscheduled, unroomed, overCapacity } = stats;
  const hardConflicts = [
    {
      label: "Students double-booked",
      value: conflicts.hard_student_conflicts,
    },
    {
      label: "Instructors double-booked",
      value: conflicts.hard_instructor_conflicts,
    },
    {
      label: "Students over the daily limit",
      value: conflicts.student_gt3_per_day,
    },
    {
      label: "Instructors over the daily limit",
      value: conflicts.instructor_gt_max_per_day,
    },
  ];
  const hasHardConflicts = hardConflicts.some((c) => c.value > 0);
  const hasProblems =
    unscheduled.exams.length > 0 ||
    unroomed.exams.length > 0 ||
    overCapacity.length > 0 ||
    hasHardConflicts;

  return (
    <section aria-labelledby="stats-problems" className="space-y-3">
      <h2 id="stats-problems" className="pl-2 text-lg font-semibold">
        Needs attention
      </h2>
      {!hasProblems ? (
        <p className="flex items-center gap-2 pl-2 text-sm text-muted-foreground">
          <CircleCheck className="h-4 w-4 text-emerald-600" aria-hidden />
          Every exam has a time and a room that fits, and there are no hard
          conflicts.
        </p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {hasHardConflicts && (
            <ProblemCard
              title="Hard conflicts"
              icon={Users}
              tone="danger"
              description="People with overlapping exams or more exams in a day than allowed."
            >
              <dl className="max-w-xs space-y-1 text-sm">
                {hardConflicts
                  .filter((c) => c.value > 0)
                  .map((c) => (
                    <div key={c.label} className="flex justify-between gap-2">
                      <dt className="text-muted-foreground">{c.label}</dt>
                      <dd className="font-semibold tabular-nums">
                        {c.value.toLocaleString()}
                      </dd>
                    </div>
                  ))}
              </dl>
              {onShowConflicts && (
                <Button variant="outline" size="sm" onClick={onShowConflicts}>
                  View conflicts
                </Button>
              )}
            </ProblemCard>
          )}

          {unscheduled.exams.length > 0 && (
            <ProblemCard
              title="Unscheduled exams"
              icon={AlertTriangle}
              count={unscheduled.exams.length}
              tone="warning"
              description={`No day, time or room; ${plural(unscheduled.students, "student")} enrolled. They appear in the List view without an assignment.`}
            >
              {unscheduled.groups.map((group) => (
                <div
                  key={`${group.kind}:${group.group}`}
                  className="rounded border border-orange-200 bg-white/60 p-2 text-xs"
                >
                  <div className="font-medium text-orange-800">
                    {UNSCHEDULED_TITLES[group.kind]} {group.group}
                  </div>
                  <div className="text-muted-foreground">{group.reason}</div>
                  {group.kind !== "section" && (
                    <Collapsible summary={plural(group.crns.length, "CRN")}>
                      <div className="font-mono text-muted-foreground">
                        {group.crns.join(", ")}
                      </div>
                    </Collapsible>
                  )}
                </div>
              ))}
              {unscheduled.otherCrns.length > 0 && (
                <Collapsible
                  summary={
                    unscheduled.groups.length > 0
                      ? plural(unscheduled.otherCrns.length, "other CRN")
                      : plural(unscheduled.otherCrns.length, "CRN")
                  }
                >
                  <ExamList
                    exams={unscheduled.exams.filter((e) =>
                      unscheduled.otherCrns.includes(e.crn),
                    )}
                  />
                </Collapsible>
              )}
            </ProblemCard>
          )}

          {unroomed.exams.length > 0 && (
            <ProblemCard
              title="Exams without a room"
              icon={Ban}
              count={unroomed.exams.length}
              tone="warning"
              description={`A day and time, but every fitting room was blocked; ${plural(unroomed.students, "student")} enrolled. Reduce blockouts or add rooms.`}
            >
              <Collapsible summary={plural(unroomed.exams.length, "CRN")}>
                <ExamList exams={unroomed.exams} />
              </Collapsible>
            </ProblemCard>
          )}

          {overCapacity.length > 0 && (
            <ProblemCard
              title="Rooms over capacity"
              icon={Building2}
              count={overCapacity.length}
              tone="warning"
              description="Exams placed in a room with fewer seats than students."
            >
              <Collapsible summary={plural(overCapacity.length, "exam")}>
                <ul className="space-y-0.5 font-mono text-muted-foreground">
                  {overCapacity.map((e) => (
                    <li key={e.crn}>
                      {e.crn} {e.course && `· ${e.course}`} · {e.size}/
                      {e.capacity} in {e.room}
                    </li>
                  ))}
                </ul>
              </Collapsible>
            </ProblemCard>
          )}
        </div>
      )}
    </section>
  );
}
