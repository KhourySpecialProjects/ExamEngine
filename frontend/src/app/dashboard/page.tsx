"use client";

import { useEffect, useState } from "react";
import { ViewTabSwitcher } from "@/components/common/ViewTabSwitcher";
import CompactView from "@/components/visualization/calendar/CompactView";
import DensityView from "@/components/visualization/calendar/DensityView";
import { ExamListDialog } from "@/components/visualization/calendar/ExamListDialog";
import ListView from "@/components/visualization/list/ListView";
import { StatisticsDashboard } from "@/components/statistics/StatisticsDashboard";
import { useScheduleStore } from "@/lib/store/scheduleStore";
import {
  generateSampleData,
  wrapSampleDataAsScheduleResult,
} from "@/lib/utils";

type ViewType = "density" | "compact" | "list" | "statistics";

export default function DashboardPage() {
  const [activeView, setActiveView] = useState<ViewType>("density");
  const setScheduleData = useScheduleStore((state) => state.setScheduleData);

  useEffect(() => {
    const data = generateSampleData();
    const wrapped_data = wrapSampleDataAsScheduleResult(data);
    setScheduleData(wrapped_data);
  }, [setScheduleData]);

  return (
    <div className="space-y-6 m-5">
      <div className="flex items-center justify-between">
        <ViewTabSwitcher activeView={activeView} onViewChange={setActiveView} />
      </div>

      {activeView === "density" && <DensityView />}
      {activeView === "compact" && <CompactView />}
      {activeView === "list" && <ListView />}
      {activeView === "statistics" && <StatisticsDashboard />}

      <ExamListDialog />
    </div>
  );
}
