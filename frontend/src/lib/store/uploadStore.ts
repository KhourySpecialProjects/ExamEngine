// lib/stores/upload.store.ts
import { create } from "zustand";
import { apiClient } from "@/lib/api/client";
import type {
  FileSlot,
  UploadedFile,
  UploadState,
  UploadStatus,
} from "@/lib/types/upload.types";

const INITIAL_SLOTS: FileSlot[] = [
  {
    id: "courses",
    label: "Courses Data",
    description:
      "ClassCensus_clean.csv (CRN, course_ref, Course_Subject_Code, Course_Number, num_students)",
    file: null,
  },
  {
    id: "enrollments",
    label: "Enrollment Data",
    description: "Enrollment_clean.csv (student_id, CRN)",
    file: null,
  },
  {
    id: "rooms",
    label: "Room Availability",
    description: "Classrooms_clean.csv (room_name, capacity)",
    file: null,
  },
];

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

    if (filesToUpload.length !== 3) {
      throw new Error(
        "All three files are required (courses, enrollments, rooms)",
      );
    }

    set({ isUploading: true });

    try {
      // Set all files to uploading status
      filesToUpload.forEach((slot) => {
        get().updateSlotStatus(slot.id, "uploading");
      });

      // Prepare files object for API
      const coursesSlot = state.slots.find((s) => s.id === "courses");
      const enrollmentsSlot = state.slots.find((s) => s.id === "enrollments");
      const roomsSlot = state.slots.find((s) => s.id === "rooms");

      if (!coursesSlot?.file || !enrollmentsSlot?.file || !roomsSlot?.file) {
        throw new Error("Missing required files");
      }

      // Upload all files at once
      const result = await apiClient.uploadDataset({
        courses: coursesSlot.file.file,
        enrollments: enrollmentsSlot.file.file,
        rooms: roomsSlot.file.file,
      });

      // Store dataset ID
      set({ datasetId: result.dataset_id });

      // Update each slot with success and row counts
      get().updateSlotStatus("courses", "success", {
        rowCount: result.files.courses.rows,
      });
      get().updateSlotStatus("enrollments", "success", {
        rowCount: result.files.enrollments.rows,
      });
      get().updateSlotStatus("rooms", "success", {
        rowCount: result.files.rooms.rows,
      });

      return result;
    } catch (error) {
      // Mark all uploading files as error
      state.slots.forEach((slot) => {
        if (slot.file?.status === "uploading") {
          get().updateSlotStatus(slot.id, "error", {
            error: error instanceof Error ? error.message : "Upload failed",
          });
        }
      });

      throw error;
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
