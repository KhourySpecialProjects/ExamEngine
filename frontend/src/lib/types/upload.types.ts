import type { DatasetMetadata } from "@/lib/api/client";

export type UploadStatus = "pending" | "uploading" | "success" | "error";

export interface UploadedFile {
  file: File;
  status: UploadStatus;
  rowCount?: number;
  error?: string;
}

export interface FileSlot {
  id: "courses" | "enrollments" | "rooms";
  label: string;
  description: string;
  file: UploadedFile | null;
}

export interface UploadState {
  slots: FileSlot[];
  isUploading: boolean;
  datasetId: string | null;

  // Actions
  setFile: (slotId: string, file: File) => void;
  removeFile: (slotId: string) => void;
  updateSlotStatus: (
    slotId: string,
    status: UploadStatus,
    extra?: Partial<UploadedFile>,
  ) => void;
  uploadAll: () => Promise<DatasetMetadata>;
  clearAll: () => void;
  setDatasetId: (id: string | null) => void;
  reset: () => void;

  // Computed
  hasFiles: () => boolean;
  allFilesUploaded: () => boolean;
  hasErrors: () => boolean;
}

export interface FileUploadSlotProps {
  slot: FileSlot;
  onFileSelect: (file: File) => void;
  onRemove: () => void;
  disabled?: boolean;
}
