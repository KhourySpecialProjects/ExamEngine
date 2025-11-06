"use client";

import { useEffect, useState } from "react";
import { ViewTabSwitcher } from "@/components/common/ViewTabSwitcher";
import CompactView from "@/components/visualization/calendar/CompactView";
import DensityView from "@/components/visualization/calendar/DensityView";
import { ExamListDialog } from "@/components/visualization/calendar/ExamListDialog";
import ListView from "@/components/visualization/list/ListView";
import ConflictView from "@/components/visualization/list/ConflictView";
import { Button } from "@/components/ui/button";
import { DownloadCloud } from "lucide-react";
import {
  Select,
  SelectTrigger,
  SelectContent,
  SelectItem,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";
import { useScheduleData } from "@/lib/hooks/useScheduleData";
import { useCalendarStore } from "@/lib/store/calendarStore";
import { THEME_KEYS } from "@/lib/constants/colorThemes";
import { exportScheduleRowsAsCsv } from "@/lib/utils";

type ViewType = "density" | "compact" | "list" | "conflicts";

export default function DashboardPage() {
  const [activeView, setActiveView] = useState<ViewType>("density");
  const { schedule } = useScheduleData();
  const theme = useCalendarStore((s) => s.colorTheme);
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

      toast.success("Export started", { description: "Downloading schedule CSV" });
    } catch (err) {
      toast.error("Export failed", { description: err instanceof Error ? err.message : "Unknown error" });
    }
  };

  return (
    <div className="space-y-6 m-5">
      <div className="flex items-center justify-between">
        <ViewTabSwitcher activeView={activeView} onViewChange={setActiveView} />
        <div className="flex items-center gap-3">
          <Select onValueChange={(val) => setTheme(val)}>
            <SelectTrigger size="default" className="min-w-40">
              <SelectValue placeholder={theme ? theme.charAt(0).toUpperCase() + theme.slice(1) : "Theme"} />
            </SelectTrigger>
            <SelectContent>
              {THEME_KEYS.map((k) => (
                <SelectItem key={k} value={k}>
                  {k.charAt(0).toUpperCase() + k.slice(1)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Button onClick={handleExport} className="bg-black text-white hover:opacity-90" disabled={!schedule}>
            <DownloadCloud className="h-4 w-4 mr-2" />
            Export Schedule
          </Button>
        </div>
      </div>

  {activeView === "density" && <DensityView />}
  {activeView === "compact" && <CompactView />}
  {activeView === "list" && <ListView />}
  {activeView === "conflicts" && <ConflictView />}

      <ExamListDialog />
    </div>
  );
}
