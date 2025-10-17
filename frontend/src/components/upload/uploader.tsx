"use client";

import {
  AlertCircle,
  CheckCircle2,
  HardDriveDownload,
  Loader2,
  Upload,
} from "lucide-react";
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
import { useUploadStore } from "@/lib/store/uploadStore";
import { UploaderSlot } from "./UploaderSlot";
import type { FileSlot } from "@/lib/types/upload.types";

export function Uploader() {
  const slots = useUploadStore((state) => state.slots);
  const isUploading = useUploadStore((state) => state.isUploading);
  const hasFiles = useUploadStore((state) => state.hasFiles());
  const allFilesUploaded = useUploadStore((state) => state.allFilesUploaded());
  const hasErrors = useUploadStore((state) => state.hasErrors());

  const setFile = useUploadStore((state) => state.setFile);
  const removeFile = useUploadStore((state) => state.removeFile);
  const uploadAll = useUploadStore((state) => state.uploadAll);
  const clearAll = useUploadStore((state) => state.clearAll);

  const handleFileSelect = (slotId: string, file: File | null) => {
    if (!file) return;

    if (!file.name.endsWith(".csv")) {
      alert("Please upload a CSV file");
      return;
    }

    setFile(slotId, file);
  };

  const handleUploadAll = async () => {
    try {
      await uploadAll();
    } catch (error) {
      alert(error instanceof Error ? error.message : "Upload failed");
    }
  };

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button className="min-w-2xs">
          <HardDriveDownload className="h-4 " />
          Upload CSV
        </Button>
      </DialogTrigger>

      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Upload Dataset</DialogTitle>
          <DialogDescription>
            Upload three CSV files: enrollment data, room availability, and
            faculty schedules
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
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
              disabled={!hasFiles || isUploading}
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
