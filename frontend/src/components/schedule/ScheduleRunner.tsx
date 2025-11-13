"use client";

import { AlertCircle, Loader2, Play, Settings } from "lucide-react";
import { toast } from "sonner";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { useDatasetStore } from "@/lib/store/datasetStore";
import { useScheduleStore } from "@/lib/store/scheduleStore";
import { Input } from "../ui/input";

export function ScheduleRunner() {
  const selectedDatasetId = useDatasetStore((state) => state.selectedDatasetId);
  const selectedDataset = useDatasetStore((state) =>
    state.getSelectedDataset(),
  );

  const {
    currentSchedule,
    isGenerating,
    scheduleName,
    parameters,
    generateSchedule,
    setParameters,
    setScheduleName,
  } = useScheduleStore();

  const handleGenerate = async () => {
    if (!selectedDatasetId) {
      toast.error("No dataset selected", {
        description: "Please select a dataset first",
      });
      return;
    }
    if (!scheduleName || scheduleName.trim() === "") {
      toast.error("Schedule name required", {
        description: "Please enter a name for your schedule",
      });
      return;
    }

    const toastId = toast.loading("Generating schedule...", {
      description: "Running DSATUR algorithm",
    });

    try {
      const result = await generateSchedule(selectedDatasetId);
      toast.success("Schedule generated!", {
        id: toastId,
        description: `${result.schedule.total_exams} exams scheduled`,
      });
    } catch (error) {
      toast.error("Generation failed", {
        id: toastId,
        description: error instanceof Error ? error.message : "Unknown error",
      });
    }
  };
  const isGenerateDisabled =
    !selectedDatasetId || isGenerating || !scheduleName?.trim();

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button className="w-full" disabled={!selectedDatasetId}>
          <Settings className="h-4 w-4" />
          Optimize
        </Button>
      </DialogTrigger>

      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Optimize Exam Schedule</DialogTitle>
          <DialogDescription>
            Configure algorithm parameters and generate an optimized exam
            schedule
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Dataset Info */}
          {selectedDataset && (
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                <div className="font-medium">
                  {selectedDataset.dataset_name}
                </div>
                <div className="text-xs text-muted-foreground mt-1">
                  {selectedDataset.files.courses.unique_crns} courses •{" "}
                  {selectedDataset.files.enrollments.unique_students} students •{" "}
                  {selectedDataset.files.rooms.unique_rooms} rooms
                </div>
              </AlertDescription>
            </Alert>
          )}

          <div className="space-y-2">
            <Label htmlFor="schedule-name">Schedule Name</Label>
            <Input
              id="schedule-name"
              type="text"
              placeholder="e.g., Fall 2024 Final Exams"
              value={scheduleName || ""}
              onChange={(e) => setScheduleName(e.target.value)}
            />
          </div>

          {/* Parameters */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold">Algorithm Parameters</h3>

            {/* Max Exams Per Day */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label>Maximum Exams Per Student Per Day</Label>
                <span className="text-sm font-medium">
                  {parameters.student_max_per_day}
                </span>
              </div>
              <Slider
                value={[parameters.student_max_per_day || 3]}
                onValueChange={([value]) =>
                  setParameters({ student_max_per_day: value })
                }
                min={1}
                max={5}
                step={1}
                disabled={isGenerating}
              />
              <p className="text-xs text-muted-foreground">
                Limit how many exams a student can take in one day
              </p>
            </div>

            <Separator />

            {/* Max Exams Per Instructor Per Day */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label>Maximum Exams Per Instructor Per Day</Label>
                <span className="text-sm font-medium">
                  {parameters.instructor_max_per_day || 2}
                </span>
              </div>
              <Slider
                value={[parameters.instructor_max_per_day || 2]}
                onValueChange={([value]) =>
                  setParameters({ instructor_max_per_day: value })
                }
                min={1}
                max={5}
                step={1}
                disabled={isGenerating}
              />
              <p className="text-xs text-muted-foreground">
                Limit how many exams an instructor can teach in one day
              </p>
            </div>

            <Separator />

            {/* Max Days */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label>Maximum Days for Exam Period</Label>
                <span className="text-sm font-medium">
                  {parameters.max_days}
                </span>
              </div>
              <Slider
                value={[parameters.max_days || 7]}
                onValueChange={([value]) => setParameters({ max_days: value })}
                min={1}
                max={7}
                step={1}
                disabled={isGenerating}
              />
              <p className="text-xs text-muted-foreground">
                Spread exams across this many days (7 days = 1 week)
              </p>
            </div>

            <Separator />

            {/* Avoid Back-to-Back */}
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <Label>Avoid Back-to-Back Exams</Label>
                <p className="text-xs text-muted-foreground">
                  Prevent consecutive exam blocks for students and instructors
                  when possible
                </p>
              </div>
              <Switch
                checked={parameters.avoid_back_to_back}
                onCheckedChange={(checked) => {
                  if (isGenerating) return;
                  setParameters({ avoid_back_to_back: checked });
                }}
              />
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 pt-4 border-t">
            <Button
              onClick={handleGenerate}
              disabled={isGenerateDisabled}
              className="flex-1"
            >
              {isGenerating ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" />
                  Generate Schedule
                </>
              )}
            </Button>
            {/* Export removed from Optimize dialog; exporting is available from the Dashboard header */}
          </div>

          {/* Current Schedule Info */}
          {currentSchedule && (
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                <div className="font-medium">Current Schedule</div>
                <div className="text-xs text-muted-foreground mt-1">
                  {currentSchedule.schedule.total_exams} exams scheduled •{" "}
                  {currentSchedule.summary.real_conflicts} conflicts •{" "}
                  {currentSchedule.failures.length} failures
                  {currentSchedule.conflicts.total > 0 && (
                    <>
                      {" "}
                      • {currentSchedule.conflicts.total} back-to-back warnings
                    </>
                  )}
                </div>
              </AlertDescription>
            </Alert>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
