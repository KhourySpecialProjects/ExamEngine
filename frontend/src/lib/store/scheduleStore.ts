import { create } from "zustand";
import { apiClient } from "@/lib/api/client";
import type { ScheduleParameters, ScheduleResult } from "../api/schedules";

interface ScheduleState {
  // Initial data state
  currentSchedule: ScheduleResult | null;

  // UI State
  isGenerating: boolean;
  error: string | null;

  // Parameters
  parameters: ScheduleParameters;

  // Actions
  generateSchedule: (datasetId: string) => Promise<ScheduleResult>;
  setScheduleData: (schedule: ScheduleResult) => void;
  setParameters: (params: Partial<ScheduleParameters>) => void;
  clearSchedule: () => void;
  clearError: () => void;
}

export const useScheduleStore = create<ScheduleState>((set, get) => ({
  // Initial state
  currentSchedule: null,
  isGenerating: false,
  error: null,
  parameters: {
    max_per_day: 3,
    avoid_back_to_back: true,
    max_days: 7,
  },

  generateSchedule: async (datasetId: string) => {
    set({ isGenerating: true, error: null });

    try {
      const result = await apiClient.schedules.generate(
        datasetId,
        get().parameters,
      );
      set({ currentSchedule: result, isGenerating: false });
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
  // Manually set schedule data (for testing, imports, etc.)
  setScheduleData: (schedule) => {
    set({ currentSchedule: schedule, error: null });
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
