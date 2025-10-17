"use client";
import CompactView from "@/components/visualization/calendar/CompactView";
import { useEffect } from "react";
import { useCalendarStore } from "@/lib/store/calendarStore";
import { generateSampleData } from "@/lib/utils";
export default function Compact() {
  const setScheduleData = useCalendarStore((state) => state.setScheduleData);

  useEffect(() => {
    const data = generateSampleData();

    setScheduleData(data);
  }, [setScheduleData]);

  return <CompactView />;
}
