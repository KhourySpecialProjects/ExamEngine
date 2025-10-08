"use client";

import { AlertCircle, CheckCircle2, Loader2, Upload } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useUploadStore } from "@/store/upload-store";
import { UploaderSlot } from "./uploader-slot";

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
    <Card>
      <CardHeader>
        <CardTitle>Upload Dataset</CardTitle>
        <CardDescription>
          Upload three CSV files: enrollment data, room availability, and
          faculty schedules
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-3">
          {slots.map((slot) => (
            <UploaderSlot
              key={slot.id}
              slot={slot}
              onFileSelect={(file) => handleFileSelect(slot.id, file)}
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
      </CardContent>
    </Card>
  );
}
