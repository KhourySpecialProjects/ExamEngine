"use client";
import { useEffect } from "react";
import ListView from "@/components/visualization/list/ListView";
import { useScheduleStore } from "@/lib/store/scheduleStore";
import {
  generateSampleData,
  wrapSampleDataAsScheduleResult,
} from "@/lib/utils";

export default function DensityPage() {
  const setScheduleData = useScheduleStore((state) => state.setScheduleData);

  useEffect(() => {
    const data = generateSampleData();
    const wrapped_data = wrapSampleDataAsScheduleResult(data);

    setScheduleData(wrapped_data);
  }, [setScheduleData]);

  return (
    <div className="w-auto">
      <ListView />
    </div>
  );
}
