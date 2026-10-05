import { CalendarClock, CalendarPlus, Database } from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type {
  LateAddition,
  ScheduleRef,
  ScheduleResult,
} from "@/lib/api/schedules";
import { settingRows } from "@/lib/scheduleSettings";
import { cn } from "@/lib/utils";
import { conflictSummary } from "./LateAddSaveForm";

const dateTimeFormat = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  hour: "numeric",
  minute: "2-digit",
});

function RefLink({ scheduleRef }: { scheduleRef: ScheduleRef | null }) {
  if (!scheduleRef?.available || !scheduleRef.name) {
    return <span className="text-muted-foreground">Not available</span>;
  }
  return (
    <Link
      href={`/dashboard/${scheduleRef.id}`}
      className="font-medium text-foreground hover:underline"
    >
      {scheduleRef.name}
    </Link>
  );
}

function LateAdditionsTable({ additions }: { additions: LateAddition[] }) {
  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium">Late additions</h3>
      <div className="overflow-hidden rounded-md border">
        <Table aria-label="Late additions">
          <TableHeader>
            <TableRow>
              <TableHead>CRN</TableHead>
              <TableHead>Course</TableHead>
              <TableHead>Instructor</TableHead>
              <TableHead>Block</TableHead>
              <TableHead>Room</TableHead>
              <TableHead>Outcome</TableHead>
              <TableHead>Added</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {additions.map((a) => (
              <TableRow key={`${a.schedule_id}-${a.crn}`}>
                <TableCell className="font-mono">{a.crn}</TableCell>
                <TableCell>{a.course_code}</TableCell>
                <TableCell>{a.instructor_id}</TableCell>
                <TableCell>
                  {a.day_name} {a.block_time}
                </TableCell>
                <TableCell className="font-mono">{a.room}</TableCell>
                <TableCell className="whitespace-normal">
                  <span
                    className={cn(
                      "font-medium",
                      a.outcome === "clear"
                        ? "text-green-600"
                        : "text-amber-600",
                    )}
                  >
                    {a.outcome === "clear" ? "Clear" : "Least conflicts"}
                  </span>
                  <span className="block text-xs text-muted-foreground">
                    {conflictSummary(a.conflicts)}
                  </span>
                </TableCell>
                <TableCell>
                  {a.added_by_name}
                  <span className="block text-xs text-muted-foreground">
                    {dateTimeFormat.format(new Date(a.added_at))}
                  </span>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

/** Source dataset, authorship, late-add lineage and generation settings for one schedule. */
export function ScheduleDetails({ schedule }: { schedule: ScheduleResult }) {
  const lineage = schedule.lineage;
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
            <span>{lineage?.based_on ? "Saved" : "Generated"}</span>
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
          {lineage?.based_on && (
            <div className="flex flex-wrap items-center gap-2 text-muted-foreground">
              <CalendarPlus className="h-4 w-4" />
              <span>Late add to</span>
              <RefLink scheduleRef={lineage.based_on} />
              <span className="mx-1">•</span>
              <span>Original:</span>
              <RefLink scheduleRef={lineage.original} />
            </div>
          )}
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
        {lineage && lineage.late_additions.length > 0 && (
          <>
            <Separator />
            <LateAdditionsTable additions={lineage.late_additions} />
          </>
        )}
      </CardContent>
    </Card>
  );
}
