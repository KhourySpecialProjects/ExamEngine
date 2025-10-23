"use client";

import { useEffect } from "react";
import DensityView from "@/components/visualization/calendar/DensityView";
import { useScheduleStore } from "@/lib/store/scheduleStore";
import {
  generateSampleData,
  wrapSampleDataAsScheduleResult,
} from "@/lib/utils";

export default function DashboardPage() {
  const setScheduleData = useScheduleStore((state) => state.setScheduleData);

  useEffect(() => {
    const data = generateSampleData();
    const wrapped_data = wrapSampleDataAsScheduleResult(data);
    setScheduleData(wrapped_data);
  }, [setScheduleData]);

  return (
    <div className="space-y-6 m-5">
      <DensityView />
    </div>
  );
}
