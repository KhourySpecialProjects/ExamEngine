"use client";

import { useEffect } from "react";
import DensityView from "@/components/visualization/calendar/DensityView";
import { useCalendarStore } from "@/lib/store/calendarStore";
import { generateSampleData } from "@/lib/utils";

export default function DashboardPage() {
  const setScheduleData = useCalendarStore((state) => state.setScheduleData);

  useEffect(() => {
    const data = generateSampleData();
    setScheduleData(data);
  }, [setScheduleData]);

  return (
    <div className="space-y-6 m-5">
      <DensityView />
    </div>
  );
}
