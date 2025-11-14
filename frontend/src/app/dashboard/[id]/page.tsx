"use client";

import { ChevronRight, MoveLeft, Save } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { use, useEffect, useState } from "react";
import { toast } from "sonner";
import { ViewTabSwitcher } from "@/components/common/ViewTabSwitcher";
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
import ListView from "@/components/visualization/list/ListView";
import { useScheduleData } from "@/lib/hooks/useScheduleData";
import { exportScheduleRowsAsCsv } from "@/lib/utils";
import { useSchedulesStore } from "@/lib/store/schedulesStore";

type ViewType = "density" | "compact" | "list" | "statistics";

export default function SchedulePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id: scheduleId } = use(params);
  const [activeView, setActiveView] = useState<ViewType>("density");
  const router = useRouter();

  const fetchSchedule = useSchedulesStore((state) => state.fetchSchedule);

  useEffect(() => {
    fetchSchedule(scheduleId);
  }, [scheduleId, fetchSchedule]);

  const { schedule } = useScheduleData();

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
      <div className="flex items-center justify-between">
        <ViewTabSwitcher activeView={activeView} onViewChange={setActiveView} />
        <div className="flex items-center gap-3">
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
      {activeView === "statistics" && <StatisticsView />}

      <ExamListDialog />
    </div>
  );
}
