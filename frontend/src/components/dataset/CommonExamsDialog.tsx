"use client";

import { AlertTriangle, Layers, Plus, Trash2, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiClient } from "@/lib/api/client";
import { useDatasetStore } from "@/lib/store/datasetStore";
import type { CommonExamValidation } from "@/lib/types/datasets.api.types";

interface CommonGroup {
  key: string;
  label: string;
  crns: string[];
  validation?: CommonExamValidation | { is_valid: false; error: string };
}

function newGroup(index: number): CommonGroup {
  return { key: `common-${Date.now()}-${index}`, label: "", crns: [] };
}

function CrnInput({ onAddCrn }: { onAddCrn: (crn: string) => void }) {
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

function ValidationAlert({
  validation,
}: {
  validation: NonNullable<CommonGroup["validation"]>;
}) {
  if ("error" in validation) {
    return (
      <Alert variant="destructive">
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription>{validation.error}</AlertDescription>
      </Alert>
    );
  }
  return (
    <Alert variant={validation.is_valid ? "default" : "destructive"}>
      <AlertTriangle className="h-4 w-4" />
      <AlertDescription>
        <div className="space-y-1">
          <div>
            {validation.warning_message ??
              (validation.is_valid
                ? "This common exam can be scheduled."
                : "This common exam cannot be scheduled.")}
          </div>
          {!validation.is_valid && (
            <div className="text-sm font-medium mt-2">
              This group will be saved but left entirely unscheduled.
            </div>
          )}
          <div className="text-xs text-muted-foreground mt-1">
            Rooms needed: {validation.room_units} • Total enrollment:{" "}
            {validation.total_enrollment} students
          </div>
        </div>
      </AlertDescription>
    </Alert>
  );
}

export function CommonExamsDialog() {
  const { selectedDatasetId, getSelectedDataset } = useDatasetStore();
  const selectedDataset = getSelectedDataset();
  const [open, setOpen] = useState(false);
  const [groups, setGroups] = useState<CommonGroup[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [mounted, setMounted] = useState(false);

  // Prevent hydration mismatch by only rendering Dialog after mount
  useEffect(() => {
    setMounted(true);
  }, []);

  const loadGroups = useCallback(async (datasetId: string) => {
    setIsLoading(true);
    try {
      const data = await apiClient.datasets.getCommonExams(datasetId);
      const loaded = Object.entries(data ?? {}).map(([label, crns], i) => ({
        key: `common-${i}`,
        label,
        crns: Array.isArray(crns) ? crns : [],
      }));
      setGroups(loaded.length > 0 ? loaded : [newGroup(0)]);
    } catch (error) {
      console.error("Failed to load common exams:", error);
      setGroups([newGroup(0)]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (open && selectedDatasetId) {
      loadGroups(selectedDatasetId);
    }
  }, [open, selectedDatasetId, loadGroups]);

  const updateGroup = (
    key: string,
    update: (g: CommonGroup) => CommonGroup,
  ) => {
    setGroups((prev) => prev.map((g) => (g.key === key ? update(g) : g)));
  };

  const addCrn = (key: string, crn: string) => {
    updateGroup(key, (g) =>
      g.crns.includes(crn)
        ? g
        : { ...g, crns: [...g.crns, crn], validation: undefined },
    );
  };

  const removeCrn = (key: string, crn: string) => {
    updateGroup(key, (g) => ({
      ...g,
      crns: g.crns.filter((c) => c !== crn),
      validation: undefined,
    }));
  };

  const validateGroup = async (key: string, crns: string[]) => {
    if (!selectedDatasetId || crns.length === 0) return;
    try {
      const validation = await apiClient.datasets.validateCommonExam(
        selectedDatasetId,
        crns,
      );
      updateGroup(key, (g) => ({ ...g, validation }));
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to validate group";
      toast.error(`Validation failed: ${message}`);
      updateGroup(key, (g) => ({
        ...g,
        validation: { is_valid: false, error: message },
      }));
    }
  };

  const handleSave = async () => {
    if (!selectedDatasetId) return;

    const nonEmpty = groups.filter((g) => g.crns.length > 0);
    if (nonEmpty.some((g) => !g.label.trim())) {
      toast.error("Every common exam group needs a name");
      return;
    }
    const labels = nonEmpty.map((g) => g.label.trim());
    if (new Set(labels).size !== labels.length) {
      toast.error("Common exam group names must be unique");
      return;
    }

    setIsSaving(true);
    try {
      if (nonEmpty.length === 0) {
        await apiClient.datasets.clearCommonExams(selectedDatasetId);
        toast.success("Common exams cleared");
      } else {
        const payload: Record<string, string[]> = {};
        for (const group of nonEmpty) {
          payload[group.label.trim()] = group.crns;
        }
        await apiClient.datasets.setCommonExams(selectedDatasetId, payload);
        toast.success("Common exams saved successfully");
      }
      setOpen(false);
    } catch (error) {
      const message = error instanceof Error ? error.message : undefined;
      toast.error("Failed to save common exams", { description: message });
    } finally {
      setIsSaving(false);
    }
  };

  if (!selectedDataset) {
    return null;
  }

  const trigger = (
    <Button className="w-full bg-violet-700 hover:bg-violet-800 text-white">
      <Layers className="h-4 w-4" />
      Common Exams
    </Button>
  );

  if (!mounted) {
    return trigger;
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Common Exams</DialogTitle>
          <DialogDescription>
            Group course sections (CRNs) that must sit their exam in the same
            time slot but in different rooms. Listing any section of a combined
            exam pulls in the whole combined exam. If a group cannot be placed
            as a whole, it is left unscheduled.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {isLoading ? (
            <div className="text-center py-8">Loading common exams...</div>
          ) : (
            <>
              {groups.map((group, index) => (
                <div
                  key={group.key}
                  className="border rounded-lg p-4 space-y-3"
                >
                  <div className="flex items-center justify-between gap-2">
                    <Label
                      htmlFor={`${group.key}-label`}
                      className="text-sm font-medium shrink-0"
                    >
                      Common Group {index + 1}
                    </Label>
                    <Input
                      id={`${group.key}-label`}
                      placeholder="Group name (e.g. BIOL101)"
                      value={group.label}
                      onChange={(e) =>
                        updateGroup(group.key, (g) => ({
                          ...g,
                          label: e.target.value,
                        }))
                      }
                      className="flex-1"
                    />
                    {groups.length > 1 && (
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() =>
                          setGroups((prev) =>
                            prev.filter((g) => g.key !== group.key),
                          )
                        }
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                  </div>

                  <div className="space-y-2">
                    <div className="flex gap-2">
                      <CrnInput onAddCrn={(crn) => addCrn(group.key, crn)} />
                      {group.crns.length > 0 && (
                        <Button
                          type="button"
                          variant="outline"
                          onClick={() => validateGroup(group.key, group.crns)}
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
                              onClick={() => removeCrn(group.key, crn)}
                              className="hover:text-destructive"
                            >
                              <X className="h-3 w-3" />
                            </button>
                          </div>
                        ))}
                      </div>
                    )}

                    {group.validation && (
                      <ValidationAlert validation={group.validation} />
                    )}
                  </div>
                </div>
              ))}

              <Button
                type="button"
                variant="outline"
                onClick={() =>
                  setGroups((prev) => [...prev, newGroup(prev.length)])
                }
                className="w-full"
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Common Group
              </Button>
            </>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={isSaving}>
            {isSaving ? "Saving..." : "Save Common Exams"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
