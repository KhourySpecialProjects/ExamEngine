"use client";

import { Save } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { ViewTabSwitcher } from "@/components/common/ViewTabSwitcher";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import CompactView from "@/components/visualization/calendar/CompactView";
import DensityView from "@/components/visualization/calendar/DensityView";
import { ExamListDialog } from "@/components/visualization/calendar/ExamListDialog";
import ListView from "@/components/visualization/list/ListView";
import { StatisticsView } from "@/components/statistics/StatisticsView";
import { THEME_KEYS } from "@/lib/constants/colorThemes";
import { useScheduleData } from "@/lib/hooks/useScheduleData";
import { useCalendarStore } from "@/lib/store/calendarStore";
import { exportScheduleRowsAsCsv } from "@/lib/utils";

type ViewType = "density" | "compact" | "list" | "statistics";

export default function DashboardPage() {
  const [activeView, setActiveView] = useState<ViewType>("density");
  const { schedule } = useScheduleData();
  const setTheme = useCalendarStore((s) => s.setColorTheme);

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
      <div className="flex items-center justify-between">
        <ViewTabSwitcher activeView={activeView} onViewChange={setActiveView} />
        <div className="flex items-center gap-3">
          <Select onValueChange={(val) => setTheme(val)}>
            <SelectTrigger size="default" className="min-w-30">
              <SelectValue placeholder={"Choose a Theme"} />
            </SelectTrigger>
            <SelectContent>
              {THEME_KEYS.map((k) => (
                <SelectItem key={k} value={k}>
                  Theme: {k.charAt(0).toUpperCase() + k.slice(1)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

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
