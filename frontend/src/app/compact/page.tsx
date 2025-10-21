"use client";
import CompactView from "@/components/visualization/calendar/CompactView";
import { useEffect } from "react";
import {
  generateSampleData,
  wrapSampleDataAsScheduleResult,
} from "@/lib/utils";
import { useScheduleStore } from "@/lib/store/scheduleStore";
export default function Compact() {
  const setScheduleData = useScheduleStore((state) => state.setScheduleData);

  useEffect(() => {
    const data = generateSampleData();
    const wrapped_data = wrapSampleDataAsScheduleResult(data);

    setScheduleData(wrapped_data);
  }, [setScheduleData]);

  return <CompactView />;
}
