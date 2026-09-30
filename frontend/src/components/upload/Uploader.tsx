"use client";

import {
  AlertCircle,
  CheckCircle2,
  HardDriveDownload,
  Loader2,
  Upload,
} from "lucide-react";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useDatasetStore } from "@/lib/store/datasetStore";
import { useUploadStore } from "@/lib/store/uploadStore";
import type { FileSlot } from "@/lib/types/upload.types";
import { UploaderSlot } from "./UploaderSlot";

export function Uploader() {
  const slots = useUploadStore((state) => state.slots);
  const isUploading = useUploadStore((state) => state.isUploading);
  const datasetName = useUploadStore((state) => state.datasetName);
  const hasFiles = useUploadStore((state) => state.hasFiles());
  const allFilesUploaded = useUploadStore((state) => state.allFilesUploaded());
  const hasErrors = useUploadStore((state) => state.hasErrors());
  const selectDataset = useDatasetStore((state) => state.selectDataset);

  const setFile = useUploadStore((state) => state.setFile);
  const setDatasetName = useUploadStore((state) => state.setDatasetName);
  const removeFile = useUploadStore((state) => state.removeFile);
  const uploadAll = useUploadStore((state) => state.uploadAll);
  const clearAll = useUploadStore((state) => state.clearAll);

  const handleFileSelect = (slotId: string, file: File | null) => {
    if (!file) return;

    if (!file.name.endsWith(".csv")) {
      toast.error("Invalid file type", {
        description: "Please upload a CSV file",
      });
      return;
    }

    setFile(slotId, file);
    toast.success("File added", {
      description: `${file.name} ready to upload`,
    });
  };

  const handleUploadAll = async () => {
    const uploadToast = toast.loading("Uploading dataset...", {
      description: "Please wait while we process your files",
    });
    try {
      const result = await uploadAll();
      toast.success("Upload successful!", {
        id: uploadToast,
        description: `${result.dataset_name} uploaded with ${result.files.courses.rows} courses`,
      });
      const overCapacityGroups =
        result.files.combined_exams?.over_capacity_groups ?? [];
      if (overCapacityGroups.length > 0) {
        const groupNames = overCapacityGroups.map((g) => g.group).join(", ");
        toast.warning("Some combined exams exceed room capacity", {
          description: `${groupNames}: combined enrollment exceeds the largest room, so these will be left unscheduled.`,
        });
      }
      const infeasibleGroups =
        result.files.common_exams?.infeasible_groups ?? [];
      if (infeasibleGroups.length > 0) {
        const details = infeasibleGroups
          .map((g) => `${g.group} (${g.reason})`)
          .join("; ");
        toast.warning("Some common exams cannot fit the room inventory", {
          description: `${details}. These groups will be left unscheduled.`,
        });
      }
      const overlapGroups =
        result.files.common_exams?.student_overlap_groups ?? [];
      if (overlapGroups.length > 0) {
        const details = overlapGroups
          .map(
            (g) =>
              `${g.group} (${g.students} student${g.students === 1 ? "" : "s"})`,
          )
          .join("; ");
        toast.warning(
          "Students enrolled in multiple sections of a common exam",
          {
            description: `${details}. These students will have simultaneous exams.`,
          },
        );
      }
      selectDataset(result.dataset_id);
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "Upload failed";

      try {
        const errorData = JSON.parse(errorMessage);
        if (errorData.errors) {
          const errorList = Object.entries(errorData.errors)
            .map(([file, msg]) => `${file}: ${msg}`)
            .join(", ");

          toast.error("Validation failed", {
            id: uploadToast,
            description: errorList,
          });
        } else {
          toast.error("Upload failed", {
            id: uploadToast,
            description: errorData.message || errorMessage,
          });
        }
      } catch {
        toast.error("Upload failed", {
          id: uploadToast,
          description: errorMessage,
        });
      }
    }
  };

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button id="upload-id" className="w-full">
          <HardDriveDownload className="h-4" />
          Upload CSV
        </Button>
      </DialogTrigger>

      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Upload Dataset</DialogTitle>
          <DialogDescription>
            Upload three required CSV files: courses, enrollments, and rooms.
            Optionally include room blockouts, combined exams, and common exams
            files.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="dataset-name">Dataset Name</Label>
            <Input
              id="dataset-name"
              type="text"
              placeholder="e.g., Fall 2024 Final Exams"
              value={datasetName || ""}
              onChange={(e) => setDatasetName(e.target.value)}
            />
          </div>
          <div className="space-y-3">
            {slots.map((slot: FileSlot) => (
              <UploaderSlot
                key={slot.id}
                slot={slot}
                onFileSelect={(file: File | null) =>
                  handleFileSelect(slot.id, file)
                }
                onRemove={() => removeFile(slot.id)}
                disabled={isUploading}
              />
            ))}
          </div>

          <div className="flex gap-3 pt-4 border-t">
            <Button
              onClick={handleUploadAll}
              disabled={!hasFiles || !datasetName || isUploading}
              className="flex-1"
            >
              {isUploading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Uploading...
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4 mr-2" />
                  Upload All Files
                </>
              )}
            </Button>

            <Button variant="outline" onClick={clearAll} disabled={isUploading}>
              Clear All
            </Button>
          </div>

          {allFilesUploaded && !hasErrors && hasFiles && (
            <Alert>
              <CheckCircle2 className="h-4 w-4" />
              <AlertDescription>
                All files uploaded successfully! You can now generate the exam
                schedule.
              </AlertDescription>
            </Alert>
          )}

          {hasErrors && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                Some files failed to upload. Please try again.
              </AlertDescription>
            </Alert>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
