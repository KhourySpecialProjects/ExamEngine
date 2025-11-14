import { create } from "zustand";
import { apiClient } from "@/lib/api/client";
import type { ScheduleParameters, ScheduleResult } from "../api/schedules";

interface ScheduleState {
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
  setScheduleData: (schedule: ScheduleResult) => void;
  setScheduleName: (name: string) => void;
  setParameters: (params: Partial<ScheduleParameters>) => void;
  clearSchedule: () => void;
  clearError: () => void;
}

export const useScheduleStore = create<ScheduleState>((set, get) => ({
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
    prioritize_large_courses: false,
  },

  generateSchedule: async (datasetId: string) => {
    set({ isGenerating: true, error: null });

    try {
      const result = await apiClient.schedules.generate(
        datasetId,
        get().scheduleName,
        get().parameters,
      );
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
