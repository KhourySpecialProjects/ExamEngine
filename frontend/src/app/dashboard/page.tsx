"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { ScheduleListView } from "@/components/schedules/ScheduleListView";
import type { ScheduleListItem } from "@/lib/api/schedules";
import { apiClient } from "@/lib/api/client";
import { Loader2 } from "lucide-react";
import { useSchedulesStore } from "@/lib/store/schedulesStore";

export default function DashboardPage() {
  const schedules = useSchedulesStore((state) => state.schedules);
  const isLoadingList = useSchedulesStore((state) => state.isLoadingList);
  const error = useSchedulesStore((state) => state.error);
  const fetchSchedules = useSchedulesStore((state) => state.fetchSchedules);


  useEffect(() => {
    fetchSchedules().catch((err) => {
      toast.error("Failed to load schedules", {
        description:
          err instanceof Error ? err.message : "Failed to load schedules",
      });
    });
  }, [fetchSchedules]);

  const handleDelete = async (scheduleId: string) => {
    toast.info("Delete functionality", {
      description: "Schedule deletion will be implemented soon",
    });
  };

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Manage Your Schedules</h1>
          <p className="text-muted-foreground">
            View and manage your exam schedules
          </p>
        </div>
      </div>

      {isLoadingList && (
        <div className="flex items-center justify-center py-12">
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              Loading schedules...
            </p>
          </div>
        </div>
      )}

      {error && !isLoadingList && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
          <p className="text-sm text-destructive">{error}</p>
        </div>
      )}

      {!isLoadingList && !error && (
        <ScheduleListView schedules={schedules} onDelete={handleDelete} />
      )}
    </div>
  );
}
