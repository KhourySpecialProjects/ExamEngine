import { create } from "zustand";
import { apiClient } from "@/lib/api/client";
import type { SchedulesState } from "@/lib/types/schedule.types";
import { useAuthStore } from "./authStore";

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

  deleteSchedule: async (scheduleId: string) => {
    set({ error: null });
    try {
      await apiClient.schedules.delete(scheduleId);
      set((state) => {
        const remaining = state.schedules.filter(
          (schedule) => schedule.schedule_id !== scheduleId,
        );
        const currentSchedule =
          state.currentSchedule?.schedule_id === scheduleId
            ? null
            : state.currentSchedule;
        return {
          schedules: remaining,
          currentSchedule,
        };
      });
    } catch (error) {
      set({
        error:
          error instanceof Error ? error.message : "Failed to delete schedule",
      });
      throw error;
    }
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
          error instanceof Error ? error.message : "Failed to load schedules",
        isLoadingList: false,
      });
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
          created_by_user_name: useAuthStore.getState().user?.name || "You",
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
