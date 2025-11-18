import { create } from "zustand";
import { apiClient } from "@/lib/api/client";
import type {
  ScheduleListItem,
  ScheduleParameters,
  ScheduleResult,
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
  fetchSchedules: (options?: { suppressError?: boolean }) => Promise<void>;
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
  fetchSchedules: async (options) => {
    set({ isLoadingList: true, error: null });
    try {
      const data = await apiClient.schedules.list();
      set({ schedules: data, isLoadingList: false });
    } catch (error) {
      set({
        error:
          error instanceof Error ? error.message : "Failed to load schedules",
        isLoadingList: false,
      });
      if (!options?.suppressError) {
        throw error;
      }
    }
  },

  generateSchedule: async (datasetId: string) => {
    const name = get().scheduleName?.trim() || "Untitled schedule";
    const params = get().parameters;
    const tempId = `temp-${Date.now()}`;

    set((state) => ({
      isGenerating: true,
      error: null,
      schedules: [
        {
          schedule_id: tempId,
          schedule_name: name,
          created_at: new Date().toISOString(),
          algorithm: "DSATUR",
          parameters: params,
          status: "Running",
          dataset_id: datasetId,
          total_exams: 0,
        },
        ...state.schedules,
      ],
    }));

    try {
      const result = await apiClient.schedules.generate(
        datasetId,
        name,
        params,
      );

      set((state) => ({
        currentSchedule: result,
        scheduleName: "",
        isGenerating: false,
        schedules: state.schedules.map((schedule) =>
          schedule.schedule_id === tempId
            ? {
                ...schedule,
                schedule_id: result.schedule_id,
                schedule_name: result.schedule_name,
                status: "Completed",
                total_exams: result.schedule.total_exams,
                parameters: result.parameters,
                dataset_id: result.dataset_id,
              }
            : schedule,
        ),
      }));

      await get().fetchSchedules({ suppressError: true });
      return result;
    } catch (error) {
      set((state) => ({
        error:
          error instanceof Error
            ? error.message
            : "Failed to generate schedule",
        isGenerating: false,
        schedules: state.schedules.filter(
          (schedule) => schedule.schedule_id !== tempId,
        ),
      }));
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
