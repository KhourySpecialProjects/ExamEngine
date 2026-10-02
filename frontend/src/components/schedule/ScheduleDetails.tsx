import { CalendarClock, Database } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import type { ScheduleResult } from "@/lib/api/schedules";

/** Blocks per day every schedule used before the option was recorded. */
const LEGACY_BLOCKS_PER_DAY = 5;

export interface GenerationSetting {
  label: string;
  value: string;
  note?: string;
}

const dateTimeFormat = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  hour: "numeric",
  minute: "2-digit",
});

function yesNo(value: boolean | undefined): string {
  if (value === undefined) return "Not recorded";
  return value ? "Yes" : "No";
}

function count(value: number | undefined): string {
  return value === undefined ? "Not recorded" : String(value);
}

/**
 * The settings a schedule was generated with, as stored on its run.
 *
 * Runs from before a setting was recorded show the value the generator used
 * then, marked as not recorded.
 */
export function generationSettings(
  schedule: Pick<ScheduleResult, "algorithm" | "parameters">,
): GenerationSetting[] {
  const params = schedule.parameters ?? {};
  // `parameters.algorithm` exists only on runs since the algorithm became
  // selectable; earlier runs were all DSATUR, recorded in `algorithm`.
  const isOptimized =
    (params.algorithm ?? schedule.algorithm?.toLowerCase()) === "annealing";

  const settings: GenerationSetting[] = [
    {
      label: "Algorithm",
      value: isOptimized ? "Optimized (annealing)" : "Classic (DSATUR)",
    },
  ];
  if (isOptimized) {
    settings.push({
      label: "Optimization time",
      value:
        params.time_budget_seconds === undefined
          ? "Not recorded"
          : `${params.time_budget_seconds}s`,
    });
  }
  settings.push(
    { label: "Max exam days", value: count(params.max_days) },
    params.blocks_per_day === undefined
      ? {
          label: "Exam blocks per day",
          value: String(LEGACY_BLOCKS_PER_DAY),
          note: "Not recorded; the only option at the time",
        }
      : { label: "Exam blocks per day", value: String(params.blocks_per_day) },
    {
      label: "Max exams per student per day",
      value: count(params.student_max_per_day),
    },
    {
      label: "Max exams per instructor per day",
      value: count(params.instructor_max_per_day),
    },
    {
      label: "Avoid back-to-back",
      value: yesNo(params.avoid_back_to_back),
      note: isOptimized ? undefined : "Not used by Classic",
    },
    {
      label: "Prioritize large classes",
      value: yesNo(params.prioritize_large_courses),
    },
  );
  return settings;
}

/** Source dataset, authorship and generation settings for one schedule. */
export function ScheduleDetails({ schedule }: { schedule: ScheduleResult }) {
  return (
    <Card className="gap-4 py-4">
      <CardContent className="space-y-4">
        <div className="flex flex-wrap items-center gap-x-8 gap-y-2 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <Database className="h-4 w-4 text-muted-foreground" />
            <span className="text-muted-foreground">Dataset</span>
            <span className="font-semibold text-base">
              {schedule.dataset_name}
            </span>
            {schedule.dataset_deleted && (
              <Badge variant="destructive">Deleted</Badge>
            )}
            {schedule.dataset_uploaded_at && (
              <span className="text-muted-foreground">
                uploaded{" "}
                {dateTimeFormat.format(new Date(schedule.dataset_uploaded_at))}
              </span>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-2 text-muted-foreground">
            <CalendarClock className="h-4 w-4" />
            <span>Generated</span>
            {schedule.created_at && (
              <span className="font-medium text-foreground">
                {dateTimeFormat.format(new Date(schedule.created_at))}
              </span>
            )}
            <span>by</span>
            <span className="font-medium text-foreground">
              {schedule.created_by_user_name || "Unknown"}
            </span>
            {schedule.is_shared && schedule.shared_by_user_name && (
              <>
                <span className="mx-1">•</span>
                <span>Shared by</span>
                <span className="font-medium text-foreground">
                  {schedule.shared_by_user_name}
                </span>
              </>
            )}
          </div>
        </div>
        <Separator />
        <dl className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-4 xl:grid-cols-8">
          {generationSettings(schedule).map((setting) => (
            <div key={setting.label}>
              <dt className="text-xs text-muted-foreground">{setting.label}</dt>
              <dd className="text-sm font-medium">
                {setting.value}
                {setting.note && (
                  <span className="block text-xs font-normal text-muted-foreground">
                    {setting.note}
                  </span>
                )}
              </dd>
            </div>
          ))}
        </dl>
      </CardContent>
    </Card>
  );
}
