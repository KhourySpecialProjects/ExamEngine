"use client";
import { useEffect } from "react";
import DensityView from "@/components/visualization/calendar/DensityView";
import { useCalendarStore } from "@/lib/store/calendarStore";
import { generateSampleData } from "@/lib/utils";

export default function DensityPage() {
  const setScheduleData = useCalendarStore((state) => state.setScheduleData);

  useEffect(() => {
    const data = generateSampleData();

    setScheduleData(data);
  }, [setScheduleData]);

  return (
    <div className="w-auto">
      <DensityView />
    </div>
  );
}
