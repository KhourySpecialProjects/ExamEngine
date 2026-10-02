"use client";

import { ChevronRight, MoveLeft, Save } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { use, useEffect, useState } from "react";
import { toast } from "sonner";
import { ViewTabSwitcher } from "@/components/common/ViewTabSwitcher";
import { ScheduleDetails } from "@/components/schedule/ScheduleDetails";
import { ShareScheduleDialog } from "@/components/schedule/ShareScheduleDialog";
import { ValidateScheduleDialog } from "@/components/schedule/ValidateScheduleDialog";
import { StatisticsView } from "@/components/statistics/StatisticsView";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import CompactView from "@/components/visualization/calendar/CompactView";
import DensityView from "@/components/visualization/calendar/DensityView";
import { ExamListDialog } from "@/components/visualization/calendar/ExamListDialog";
import ConflictView from "@/components/visualization/list/ConflictView";
import ListView from "@/components/visualization/list/ListView";
import { useScheduleData } from "@/lib/hooks/useScheduleData";
import { useAuthStore } from "@/lib/store/authStore";
import { useSchedulesStore } from "@/lib/store/schedulesStore";
import { exportScheduleRowsAsCsv } from "@/lib/utils";

type ViewType = "density" | "compact" | "list" | "statistics" | "conflicts";

export default function SchedulePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id: scheduleId } = use(params);
  const [activeView, setActiveView] = useState<ViewType>("density");
  const router = useRouter();
  const { user } = useAuthStore();

  const fetchSchedule = useSchedulesStore((state) => state.fetchSchedule);

  useEffect(() => {
    fetchSchedule(scheduleId).catch((error) => {
      toast.error("Failed to load schedule", {
        description: error instanceof Error ? error.message : "Unknown error",
      });
    });
  }, [scheduleId, fetchSchedule]);

  const { schedule } = useScheduleData();

  // Check if user owns this schedule
  const canShare = schedule?.is_owner ?? false;

  const handleExport = async () => {
    if (!schedule) {
      toast.error("No schedule to export", {
        description: "Generate a schedule first",
      });
      return;
    }

    try {
      const rows = schedule.schedule.complete;
      if (!rows || rows.length === 0) {
        toast.error("Schedule empty", { description: "Nothing to export" });
        return;
      }

      exportScheduleRowsAsCsv(rows, "schedule_exams.csv");

      toast.success("Export started", {
        description: "Downloading schedule CSV",
      });
    } catch (err) {
      toast.error("Export failed", {
        description: err instanceof Error ? err.message : "Unknown error",
      });
    }
  };

  return (
    <div className="space-y-6 m-5">
      <div className="flex items-center gap-4 mb-6">
        <Button
          variant="outline"
          size="sm"
          className="rounded-md"
          onClick={() => router.push("/dashboard")}
        >
          <MoveLeft />
          Back
        </Button>
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbLink asChild>
                <Link href="/dashboard">Schedules</Link>
              </BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator>
              <ChevronRight className="h-4 w-4" />
            </BreadcrumbSeparator>
            <BreadcrumbItem>
              <BreadcrumbPage>{schedule?.schedule_name}</BreadcrumbPage>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </div>
      {schedule && <ScheduleDetails schedule={schedule} />}
      <div className="flex items-center justify-between">
        <ViewTabSwitcher activeView={activeView} onViewChange={setActiveView} />
        <div className="flex items-center gap-3">
          {canShare && schedule && (
            <ShareScheduleDialog
              scheduleId={scheduleId}
              scheduleName={schedule.schedule_name}
              onShareUpdate={() => {
                // Optionally refresh schedule data
              }}
            />
          )}
          {schedule && (
            <ValidateScheduleDialog
              scheduleId={scheduleId}
              scheduleName={schedule.schedule_name}
            />
          )}
          <Button
            onClick={handleExport}
            className="bg-black text-white hover:opacity-90 min-w-50"
            disabled={!schedule}
          >
            <Save />
            <span>Export Schedule</span>
          </Button>
        </div>
      </div>

      {activeView === "density" && <DensityView />}
      {activeView === "compact" && <CompactView />}
      {activeView === "list" && <ListView />}
      {activeView === "statistics" && (
        <StatisticsView onShowConflicts={() => setActiveView("conflicts")} />
      )}
      {activeView === "conflicts" && <ConflictView />}

      <ExamListDialog />
    </div>
  );
}
