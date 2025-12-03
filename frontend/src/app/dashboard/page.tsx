"use client";

import { Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { ScheduleListView } from "@/components/schedules/ScheduleListView";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useSchedulesStore } from "@/lib/store/schedulesStore";

export default function DashboardPage() {
  const schedules = useSchedulesStore((state) => state.schedules);
  const isLoadingList = useSchedulesStore((state) => state.isLoadingList);
  const error = useSchedulesStore((state) => state.error);
  const fetchSchedules = useSchedulesStore((state) => state.fetchSchedules);
  const deleteSchedule = useSchedulesStore((state) => state.deleteSchedule);

  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const [isConfirmOpen, setIsConfirmOpen] = useState(false);

  const scheduleToDelete = pendingDeleteId
    ? schedules.find((s) => s.schedule_id === pendingDeleteId)
    : undefined;

  useEffect(() => {
    fetchSchedules().catch((err) => {
      toast.error("Failed to load schedules", {
        description:
          err instanceof Error ? err.message : "Failed to load schedules",
      });
    });
  }, [fetchSchedules]);

  const requestDelete = (scheduleId: string) => {
    setPendingDeleteId(scheduleId);
    setIsConfirmOpen(true);
  };

  const handleDelete = async () => {
    if (!pendingDeleteId) return;

    const toastId = toast.loading("Deleting schedule...");
    try {
      await deleteSchedule(pendingDeleteId);
      toast.success("Schedule deleted", { id: toastId });
    } catch (error) {
      toast.error("Failed to delete schedule", {
        id: toastId,
        description: error instanceof Error ? error.message : "Unknown error",
      });
    } finally {
      setIsConfirmOpen(false);
      setPendingDeleteId(null);
    }
  };

  return (
    <div id="schedule-view" className="space-y-6 p-6">
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
        <ScheduleListView schedules={schedules} onDelete={requestDelete} />
      )}

      <AlertDialog
        open={isConfirmOpen}
        onOpenChange={(open) => {
          setIsConfirmOpen(open);
          if (!open) setPendingDeleteId(null);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              Delete this schedule permanently?
            </AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone.{" "}
              <span className="font-semibold text-red-500">
                {scheduleToDelete?.schedule_name ?? "This schedule"}
              </span>{" "}
              will be removed.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete}>Delete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
