import { create } from "zustand";
import type {
  FileSlot,
  UploadedFile,
  UploadState,
  UploadStatus,
} from "@/lib/types/upload.types";

const INITIAL_SLOTS: FileSlot[] = [
  {
    id: "enrollment",
    label: "Enrollment Data",
    description: "Student course enrollment information",
    file: null,
  },
  {
    id: "rooms",
    label: "Room Availability",
    description: "Available rooms and capacities",
    file: null,
  },
  {
    id: "class",
    label: "Class Census",
    description: "Class schedules and preferences",
    file: null,
  },
];

// Upload function
async function uploadFile(
  file: File,
  type: string,
  datasetId?: string,
): Promise<{ rowCount: number }> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("type", type);
  if (datasetId) {
    formData.append("dataset_id", datasetId);
  }

  // TODO: Replace with actual API call
  await new Promise((resolve) => setTimeout(resolve, 5000));

  if (Math.random() < 0.1) {
    throw new Error("Network error occurred");
  }

  return { rowCount: Math.floor(Math.random() * 1000) + 100 };
}

export const useUploadStore = create<UploadState>((set, get) => ({
  // Initial state
  slots: INITIAL_SLOTS,
  isUploading: false,
  datasetId: null,

  // Actions
  setFile: (slotId: string, file: File) => {
    set((state) => ({
      slots: state.slots.map((slot: FileSlot) =>
        slot.id === slotId
          ? {
            ...slot,
            file: {
              file,
              status: "pending" as UploadStatus,
            },
          }
          : slot,
      ),
    }));
  },

  removeFile: (slotId: string) => {
    set((state) => ({
      slots: state.slots.map((slot) =>
        slot.id === slotId ? { ...slot, file: null } : slot,
      ),
    }));
  },

  updateSlotStatus: (
    slotId: string,
    status: UploadStatus,
    extra?: Partial<UploadedFile>,
  ) => {
    set((state) => ({
      slots: state.slots.map((slot: FileSlot) =>
        slot.id === slotId && slot.file
          ? {
            ...slot,
            file: {
              ...slot.file,
              status,
              ...extra,
            },
          }
          : slot,
      ),
    }));
  },

  uploadAll: async () => {
    const state = get();
    const filesToUpload = state.slots.filter((slot) => slot.file !== null);

    if (filesToUpload.length === 0) {
      throw new Error("No files to upload");
    }

    set({ isUploading: true });

    try {
      // TODO: Create dataset to receive dataset id

      // Upload each file
      for (const slot of filesToUpload) {
        if (!slot.file) continue;

        try {
          // Update to uploading
          get().updateSlotStatus(slot.id, "uploading");

          // Upload file
          const result = await uploadFile(
            slot.file.file,
            slot.id,
            state.datasetId || undefined,
          );

          // Update to success
          get().updateSlotStatus(slot.id, "success", {
            rowCount: result.rowCount,
          });
        } catch (error) {
          // Update to error
          get().updateSlotStatus(slot.id, "error", {
            error: error instanceof Error ? error.message : "Upload failed",
          });
        }
      }
    } finally {
      set({ isUploading: false });
    }
  },

  clearAll: () => {
    set({
      slots: INITIAL_SLOTS,
      datasetId: null,
    });
  },

  setDatasetId: (id: string | null) => {
    set({ datasetId: id });
  },

  reset: () => {
    set({
      slots: INITIAL_SLOTS,
      isUploading: false,
      datasetId: null,
    });
  },

  // Computed values
  hasFiles: () => {
    const state = get();
    return state.slots.some((slot) => slot.file !== null);
  },

  allFilesUploaded: () => {
    const state = get();
    return state.slots.every(
      (slot) => slot.file === null || slot.file.status === "success",
    );
  },

  hasErrors: () => {
    const state = get();
    return state.slots.some((slot) => slot.file?.status === "error");
  },
}));
