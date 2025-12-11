"use client";

import { useState, useEffect } from "react";
import { X, Plus, Trash2, AlertTriangle, GitMerge } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useDatasetStore } from "@/lib/store/datasetStore";
import { apiClient } from "@/lib/api/client";

interface MergeGroup {
  id: string;
  crns: string[];
  validation?: {
    is_valid: boolean;
    has_suitable_room?: boolean;
    message: string;
    warning_type?: string;
    total_enrollment?: number;
    max_room_capacity?: number;
  };
}

function CrnInputGroup({
  groupId,
  onAddCrn,
}: {
  groupId: string;
  onAddCrn: (crn: string) => void;
}) {
  const [inputValue, setInputValue] = useState("");

  const handleAdd = () => {
    const crn = inputValue.trim();
    if (crn) {
      onAddCrn(crn);
      setInputValue("");
    }
  };

  return (
    <>
      <Input
        placeholder="Enter CRN"
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            handleAdd();
          }
        }}
        className="flex-1"
      />
      <Button type="button" variant="outline" onClick={handleAdd}>
        <Plus className="h-4 w-4" />
      </Button>
    </>
  );
}

export function MergeCoursesDialog() {
  const { selectedDatasetId, getSelectedDataset } = useDatasetStore();
  const selectedDataset = getSelectedDataset();
  const [open, setOpen] = useState(false);
  const [mergeGroups, setMergeGroups] = useState<MergeGroup[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // Load existing merges when dialog opens
  useEffect(() => {
    if (open && selectedDatasetId) {
      loadMerges();
    }
  }, [open, selectedDatasetId]);

  const loadMerges = async () => {
    if (!selectedDatasetId) return;
    
    setIsLoading(true);
    try {
      const merges = await apiClient.datasets.getCourseMerges(selectedDatasetId);
      
      // Convert merges object to MergeGroup array
      const groups: MergeGroup[] = Object.entries(merges).map(([id, crns]) => ({
        id,
        crns: Array.isArray(crns) ? crns : [],
      }));
      
      setMergeGroups(groups.length > 0 ? groups : [{ id: "merge-1", crns: [] }]);
    } catch (error) {
      console.error("Failed to load merges:", error);
      setMergeGroups([{ id: "merge-1", crns: [] }]);
    } finally {
      setIsLoading(false);
    }
  };

  const addMergeGroup = () => {
    const newId = `merge-${Date.now()}`;
    setMergeGroups([...mergeGroups, { id: newId, crns: [] }]);
  };

  const removeMergeGroup = (groupId: string) => {
    setMergeGroups(mergeGroups.filter((g) => g.id !== groupId));
  };

  const addCrnToGroup = (groupId: string, crn: string) => {
    if (!crn.trim()) return;
    
    setMergeGroups(
      mergeGroups.map((group) => {
        if (group.id === groupId) {
          const crns = [...group.crns];
          if (!crns.includes(crn.trim())) {
            crns.push(crn.trim());
          }
          return { ...group, crns, validation: undefined };
        }
        return group;
      }),
    );
  };

  const removeCrnFromGroup = (groupId: string, crn: string) => {
    setMergeGroups(
      mergeGroups.map((group) => {
        if (group.id === groupId) {
          return {
            ...group,
            crns: group.crns.filter((c) => c !== crn),
            validation: undefined,
          };
        }
        return group;
      }),
    );
  };

  const validateGroup = async (groupId: string, crns: string[]) => {
    if (!selectedDatasetId || crns.length === 0) return;

    try {
      const validation = await apiClient.datasets.validateCourseMerge(
        selectedDatasetId,
        crns,
      );

      setMergeGroups(
        mergeGroups.map((group) => {
          if (group.id === groupId) {
            return { ...group, validation };
          }
          return group;
        }),
      );
    } catch (error) {
      console.error("Validation failed:", error);
      const errorMessage = error instanceof Error ? error.message : "Failed to validate merge group";
      toast.error(`Validation failed: ${errorMessage}`);
      
      // Set error state on the group
      setMergeGroups(
        mergeGroups.map((group) => {
          if (group.id === groupId) {
            return {
              ...group,
              validation: {
                is_valid: false,
                message: errorMessage,
              },
            };
          }
          return group;
        }),
      );
    }
  };

  const handleSave = async () => {
    if (!selectedDatasetId) return;

    // Filter out empty groups
    const validGroups = mergeGroups.filter((g) => g.crns.length > 0);

    if (validGroups.length === 0) {
      // Clear all merges
      try {
        setIsSaving(true);
        await apiClient.datasets.clearCourseMerges(selectedDatasetId);
        toast.success("Course merges cleared");
        setOpen(false);
      } catch (error) {
        toast.error("Failed to clear merges");
      } finally {
        setIsSaving(false);
      }
      return;
    }

    // Convert to merges object
    const merges: Record<string, string[]> = {};
    validGroups.forEach((group) => {
      merges[group.id] = group.crns;
    });

    try {
      setIsSaving(true);
      const result = await apiClient.datasets.setCourseMerges(
        selectedDatasetId,
        merges,
      );

      // Check for validation warnings
      const hasWarnings = Object.values(result.validation || {}).some(
        (v: any) => !v.is_valid && v.warning_type === "room_capacity_exceeded",
      );

      if (hasWarnings) {
        toast.warning("Merges saved with warnings. Some groups may exceed room capacity.");
      } else {
        toast.success("Course merges saved successfully");
      }

      setOpen(false);
    } catch (error) {
      toast.error("Failed to save course merges");
    } finally {
      setIsSaving(false);
    }
  };

  if (!selectedDataset || !mounted) {
    return null;
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button id="merge-courses-id" className="w-full bg-blue-700 hover:bg-blue-800 text-white" disabled={!selectedDataset}>
          <GitMerge className="h-4 w-4" />
          Merge Courses
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Merge Courses</DialogTitle>
          <DialogDescription>
            Group multiple course sections (CRNs) to schedule them together in the same time slot and room.
            Enter CRNs for each merge group.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {isLoading ? (
            <div className="text-center py-8">Loading merges...</div>
          ) : (
            <>
              {mergeGroups.map((group) => (
                <div
                  key={group.id}
                  className="border rounded-lg p-4 space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <Label className="text-sm font-medium">
                      Merge Group {mergeGroups.indexOf(group) + 1}
                    </Label>
                    {mergeGroups.length > 1 && (
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => removeMergeGroup(group.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                  </div>

                  <div className="space-y-2">
                    <div className="flex gap-2">
                      <CrnInputGroup
                        groupId={group.id}
                        onAddCrn={(crn) => addCrnToGroup(group.id, crn)}
                      />
                      {group.crns.length > 0 && (
                        <Button
                          type="button"
                          variant="outline"
                          onClick={() => validateGroup(group.id, group.crns)}
                        >
                          Validate
                        </Button>
                      )}
                    </div>

                    {group.crns.length > 0 && (
                      <div className="flex flex-wrap gap-2">
                        {group.crns.map((crn) => (
                          <div
                            key={crn}
                            className="flex items-center gap-1 bg-secondary px-2 py-1 rounded text-sm"
                          >
                            <span>{crn}</span>
                            <button
                              type="button"
                              onClick={() => removeCrnFromGroup(group.id, crn)}
                              className="hover:text-destructive"
                            >
                              <X className="h-3 w-3" />
                            </button>
                          </div>
                        ))}
                      </div>
                    )}

                    {group.validation && (
                      <Alert
                        variant={
                          group.validation.has_suitable_room === false
                            ? "destructive"
                            : group.validation.is_valid
                              ? "default"
                              : "destructive"
                        }
                      >
                        <AlertTriangle className="h-4 w-4" />
                        <AlertDescription>
                          <div className="space-y-1">
                            <div>{group.validation.message}</div>
                            {group.validation.has_suitable_room === false && (
                              <div className="text-sm font-medium mt-2">
                                ⚠️ This merge will be saved but will not be scheduled (no room assignment).
                                It will appear in the schedule as unscheduled.
                              </div>
                            )}
                            {group.validation.total_enrollment !== undefined && 
                             group.validation.max_room_capacity !== undefined && (
                              <div className="text-xs text-muted-foreground mt-1">
                                Total enrollment: {group.validation.total_enrollment} students • 
                                Max room capacity: {group.validation.max_room_capacity} students
                              </div>
                            )}
                          </div>
                        </AlertDescription>
                      </Alert>
                    )}
                  </div>
                </div>
              ))}

              <Button
                type="button"
                variant="outline"
                onClick={addMergeGroup}
                className="w-full"
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Merge Group
              </Button>
            </>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={isSaving}>
            {isSaving ? "Saving..." : "Save Merges"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

