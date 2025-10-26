"use client";

import { useEffect, useState } from "react";
import { ViewTabSwitcher } from "@/components/common/ViewTabSwitcher";
import CompactView from "@/components/visualization/calendar/CompactView";
import DensityView from "@/components/visualization/calendar/DensityView";
import { ExamListDialog } from "@/components/visualization/calendar/ExamListDialog";
import ListView from "@/components/visualization/list/ListView";

type ViewType = "density" | "compact" | "list";

export default function DashboardPage() {
  const [activeView, setActiveView] = useState<ViewType>("density");

  return (
    <div className="space-y-6 m-5">
      <div className="flex items-center justify-between">
        <ViewTabSwitcher activeView={activeView} onViewChange={setActiveView} />
      </div>

      {activeView === "density" && <DensityView />}
      {activeView === "compact" && <CompactView />}
      {activeView === "list" && <ListView />}

      <ExamListDialog />
    </div>
  );
}
