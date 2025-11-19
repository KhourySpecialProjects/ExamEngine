"use client";

import { Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { ScheduleListView } from "@/components/schedules/ScheduleListView";
import { apiClient } from "@/lib/api/client";
import type { ScheduleListItem } from "@/lib/api/schedules";

export default function DashboardPage() {
  const [schedules, setSchedules] = useState<ScheduleListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSchedules();
  }, [fetchSchedules]);

  const fetchSchedules = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await apiClient.schedules.list();
      setSchedules(data);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to load schedules";
      setError(errorMessage);
      toast.error("Failed to load schedules", {
        description: errorMessage,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (_scheduleId: string) => {
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

      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              Loading schedules...
            </p>
          </div>
        </div>
      )}

      {error && !isLoading && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
          <p className="text-sm text-destructive">{error}</p>
        </div>
      )}

      {!isLoading && !error && (
        <ScheduleListView schedules={schedules} onDelete={handleDelete} />
      )}
    </div>
  );
}
