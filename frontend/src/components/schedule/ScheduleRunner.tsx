"use client";

import { AlertCircle, ArrowRightCircle, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { ButtonGroup } from "@/components/ui/button-group";
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
import { useSchedulesStore } from "@/lib/store/schedulesStore";
import { Input } from "../ui/input";

export function ScheduleRunner() {
  const selectedDatasetId = useDatasetStore((state) => state.selectedDatasetId);
  const selectedDataset = useDatasetStore((state) =>
    state.getSelectedDataset(),
  );

  const {
    isGenerating,
    scheduleName,
    parameters,
    generateSchedule,
    setParameters,
    setScheduleName,
  } = useSchedulesStore();

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
      description:
        parameters.algorithm === "annealing"
          ? `Running Optimized (annealing, ${parameters.time_budget_seconds ?? 15}s)`
          : "Running Classic (DSATUR)",
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
        <Button
          id="generate-id"
          className="w-full bg-emerald-700 hover:bg-emerald-800 text-white"
          disabled={!selectedDatasetId}
        >
          <ArrowRightCircle className="h-4 w-4" />
          Generate Schedule
        </Button>
      </DialogTrigger>

      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
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
            <div className="space-y-2">
              <Label htmlFor="font-semibold">Dataset Name</Label>
              <Alert>
                <AlertDescription>
                  <div className="font-medium">
                    {selectedDataset.dataset_name}
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">
                    {selectedDataset.files.courses.unique_crns} courses •{" "}
                    {selectedDataset.files.enrollments.unique_students} students
                    • {selectedDataset.files.rooms.unique_rooms} rooms
                  </div>
                </AlertDescription>
              </Alert>
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="schedule-name font-semibold">Schedule Name</Label>
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

            {/* Exam Blocks Per Day */}
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <Label>Exam Blocks Per Day</Label>
                <p className="text-xs text-muted-foreground">
                  4 uses the four earliest blocks (no 6PM-8PM exams)
                </p>
              </div>
              <ButtonGroup aria-label="Exam blocks per day">
                {([4, 5] as const).map((blocks) => (
                  <Button
                    key={blocks}
                    size="sm"
                    variant={
                      parameters.blocks_per_day === blocks
                        ? "default"
                        : "outline"
                    }
                    aria-pressed={parameters.blocks_per_day === blocks}
                    onClick={() => setParameters({ blocks_per_day: blocks })}
                    disabled={isGenerating}
                  >
                    {blocks}
                  </Button>
                ))}
              </ButtonGroup>
            </div>

            <Separator />

            {/* Algorithm */}
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <Label>Algorithm</Label>
                <p className="text-xs text-muted-foreground">
                  {parameters.algorithm === "annealing"
                    ? "Saturation + annealing — searches for fewer conflicts and back-to-backs"
                    : "DSATUR greedy — the original one-pass scheduler"}
                </p>
              </div>
              <ButtonGroup aria-label="Algorithm">
                {(
                  [
                    ["dsatur", "Classic"],
                    ["annealing", "Optimized"],
                  ] as const
                ).map(([algorithm, label]) => (
                  <Button
                    key={algorithm}
                    size="sm"
                    variant={
                      parameters.algorithm === algorithm ? "default" : "outline"
                    }
                    aria-pressed={parameters.algorithm === algorithm}
                    onClick={() => setParameters({ algorithm })}
                    disabled={isGenerating}
                  >
                    {label}
                  </Button>
                ))}
              </ButtonGroup>
            </div>

            {parameters.algorithm === "annealing" && (
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <Label>Optimization Time</Label>
                  <p className="text-xs text-muted-foreground">
                    Longer runs find better schedules
                  </p>
                </div>
                <ButtonGroup aria-label="Optimization time">
                  {([5, 15, 30] as const).map((seconds) => (
                    <Button
                      key={seconds}
                      size="sm"
                      variant={
                        parameters.time_budget_seconds === seconds
                          ? "default"
                          : "outline"
                      }
                      aria-pressed={parameters.time_budget_seconds === seconds}
                      onClick={() =>
                        setParameters({ time_budget_seconds: seconds })
                      }
                      disabled={isGenerating}
                    >
                      {seconds}s
                    </Button>
                  ))}
                </ButtonGroup>
              </div>
            )}

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

            <Separator />

            {/* Large Class Priority */}
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <Label>Prioritize Large Classes</Label>
                <p className="text-xs text-muted-foreground">
                  Schedule the highest-enrollment courses first to secure
                  optimal time slots.
                </p>
              </div>
              <Switch
                checked={parameters.prioritize_large_courses ?? false}
                onCheckedChange={(checked) => {
                  if (isGenerating) return;
                  setParameters({ prioritize_large_courses: checked });
                }}
                disabled={isGenerating}
              />
            </div>

            <Separator />

            {/* Room Promotion */}
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <Label htmlFor="promote-rooms">Promote to Larger Rooms</Label>
                <p className="text-xs text-muted-foreground">
                  After scheduling, move the fullest exams into larger free
                  rooms in the same block, up to twice their enrollment (room
                  for alternate-seat spacing)
                </p>
              </div>
              <Switch
                id="promote-rooms"
                checked={parameters.promote_rooms ?? false}
                onCheckedChange={(checked) => {
                  if (isGenerating) return;
                  setParameters({ promote_rooms: checked });
                }}
                disabled={isGenerating}
              />
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 pt-4 border-t">
            <Button
              onClick={handleGenerate}
              disabled={isGenerateDisabled}
              className="flex-1 bg-emerald-700 hover:bg-emerald-800 text-white"
            >
              {isGenerating ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <ArrowRightCircle className="h-4 w-4" />
                  Generate Schedule
                </>
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
