"use client";

import { useEffect, useState } from "react";
import { ViewTabSwitcher } from "@/components/common/ViewTabSwitcher";
import CompactView from "@/components/visualization/calendar/CompactView";
import DensityView from "@/components/visualization/calendar/DensityView";
import { ExamListDialog } from "@/components/visualization/calendar/ExamListDialog";
import ListView from "@/components/visualization/list/ListView";
import { Button } from "@/components/ui/button";
import { DownloadCloud } from "lucide-react";
import { toast } from "sonner";
import { useScheduleData } from "@/lib/hooks/useScheduleData";

type ViewType = "density" | "compact" | "list";

export default function DashboardPage() {
  const [activeView, setActiveView] = useState<ViewType>("density");
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

      const headers = Object.keys(rows[0]);
      const csvLines = [headers.join(",")];
      for (const r of rows) {
        const values = headers.map((h) => {
          const v = (r as any)[h];
          if (v === null || v === undefined) return "";
          const s = String(v).replace(/"/g, '""');
          return s.includes(",") || s.includes('"') ? `"${s}"` : s;
        });
        csvLines.push(values.join(","));
      }

      const csvContent = csvLines.join("\n");
      const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `schedule_exams.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);

      toast.success("Export started", { description: "Downloading schedule CSV" });
    } catch (err) {
      toast.error("Export failed", { description: err instanceof Error ? err.message : "Unknown error" });
    }
  };

  return (
    <div className="space-y-6 m-5">
      <div className="flex items-center justify-between">
        <ViewTabSwitcher activeView={activeView} onViewChange={setActiveView} />
        <div>
          <Button onClick={handleExport} variant="outline" disabled={!schedule}>
            <DownloadCloud className="h-4 w-4 mr-2" />
            Export Schedule
          </Button>
        </div>
      </div>

      {activeView === "density" && <DensityView />}
      {activeView === "compact" && <CompactView />}
      {activeView === "list" && <ListView />}

      <ExamListDialog />
    </div>
  );
}
