import { CalendarClock, Database } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import type { ScheduleResult } from "@/lib/api/schedules";
import { settingRows } from "@/lib/scheduleSettings";
import { cn } from "@/lib/utils";

const dateTimeFormat = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  hour: "numeric",
  minute: "2-digit",
});

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
          {settingRows(schedule.summary).map((setting) => (
            <div key={setting.key}>
              <dt className="text-xs text-muted-foreground">{setting.label}</dt>
              <dd
                className={cn(
                  "text-sm font-medium",
                  setting.unused && "font-normal text-muted-foreground",
                )}
              >
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
