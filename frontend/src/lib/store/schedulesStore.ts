import { create } from "zustand";
import { apiClient } from "@/lib/api/client";
import type { 
  ScheduleParameters, 
  ScheduleResult, 
  ScheduleListItem,
} from "../api/schedules";

interface SchedulesState {
  // List state
  schedules: ScheduleListItem[];
  isLoadingList: boolean;

  // Initial data state
  currentSchedule: ScheduleResult | null;
  scheduleName: string;

  // UI State
  isGenerating: boolean;
  error: string | null;

  // Parameters
  parameters: ScheduleParameters;

  // Actions
  generateSchedule: (datasetId: string) => Promise<ScheduleResult>;
  fetchSchedule: (scheduleId: string) => Promise<ScheduleResult>;
  fetchSchedules: () => Promise<void>;
  setScheduleData: (schedule: ScheduleResult) => void;
  setScheduleName: (name: string) => void;
  setParameters: (params: Partial<ScheduleParameters>) => void;
  clearSchedule: () => void;
  clearError: () => void;
}

export const useSchedulesStore = create<SchedulesState>((set, get) => ({
  // List state
  schedules: [],
  isLoadingList: false,

  // Initial state
  currentSchedule: null,
  scheduleName: "",
  isGenerating: false,
  error: null,
  parameters: {
    student_max_per_day: 3,
    instructor_max_per_day: 2,
    avoid_back_to_back: true,
    max_days: 7,
  },

  // Load all schedules into the store
  fetchSchedules: async () => {
    set({ isLoadingList: true, error: null });
    try {
      const data = await apiClient.schedules.list();
      set({ schedules: data, isLoadingList: false });
    } catch (error) {
      set({
        error:
          error instanceof Error
            ? error.message
            : "Failed to load schedules",
        isLoadingList: false,
      });
      throw error;
    }
  },

  generateSchedule: async (datasetId: string) => {
    set({ isGenerating: true, error: null });

    try {
      const result = await apiClient.schedules.generate(
        datasetId,
        get().scheduleName,
        get().parameters,
      );

      // Refresh list inside the store after a successful generation
      let updatedList = get().schedules;
      try {
        const data = await apiClient.schedules.list();
        updatedList = data;
      } catch {
        // If the list refresh fails, don't block schedule generation
      }

      set({ currentSchedule: result, scheduleName: "", isGenerating: false });
      return result;
    } catch (error) {
      set({
        error:
          error instanceof Error
            ? error.message
            : "Failed to generate schedule",
        isGenerating: false,
      });
      throw error;
    }
  },

  fetchSchedule: async (scheduleId: string) => {
    set({ isGenerating: true, error: null });
    try {
      const result = await apiClient.schedules.get(scheduleId);
      set({ currentSchedule: result, isGenerating: false });
      return result;
    } catch (error) {
      set({
        error:
          error instanceof Error ? error.message : "Failed to fetch schedule",
        isGenerating: false,
      });
      throw error;
    }
  },
  
  // Manually set schedule data (for testing, imports, etc.)
  setScheduleData: (schedule) => {
    set({ currentSchedule: schedule, error: null });
  },

  setScheduleName: (name: string) => {
    set({ scheduleName: name });
  },

  // Update parameters
  setParameters: (params) => {
    set((state) => ({
      parameters: { ...state.parameters, ...params },
    }));
  },

  // Clear schedule
  clearSchedule: () => {
    set({ currentSchedule: null, error: null });
  },

  // Clear error
  clearError: () => {
    set({ error: null });
  },
}));
