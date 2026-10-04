"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { compareHref } from "@/lib/scheduleSelection";
import { useSchedulesViewStore } from "@/lib/store/schedulesViewStore";

/** Pinned to the bottom of the schedules page while any schedule is picked. */
export function ScheduleSelectionBar() {
  const selectedIds = useSchedulesViewStore((s) => s.selectedIds);
  const setSelectedIds = useSchedulesViewStore((s) => s.setSelectedIds);

  if (selectedIds.length === 0) return null;

  return (
    <section
      aria-label="Selected schedules"
      className="sticky bottom-4 z-10 mx-auto flex w-fit items-center gap-3 rounded-xl border bg-card px-4 py-2 shadow-lg"
    >
      <span className="text-sm font-medium">{selectedIds.length} selected</span>
      {selectedIds.length < 2 ? (
        // A disabled button gets no hover: the wrapper shows why.
        <span title="Select at least 2 schedules to compare">
          <Button size="sm" disabled>
            Compare
          </Button>
        </span>
      ) : (
        <Button size="sm" asChild>
          <Link href={compareHref(selectedIds)}>Compare</Link>
        </Button>
      )}
      <Button size="sm" variant="ghost" onClick={() => setSelectedIds([])}>
        Clear
      </Button>
    </section>
  );
}
