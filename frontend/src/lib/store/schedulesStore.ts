import { create } from "zustand";
import { apiClient } from "@/lib/api/client";
import { LATE_ADD_ALGORITHM, type ScheduleListItem } from "@/lib/api/schedules";
import type { SchedulesState } from "@/lib/types/schedule.types";
import { useAuthStore } from "./authStore";
import { useDatasetStore } from "./datasetStore";

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
    blocks_per_day: 5,
    algorithm: "dsatur",
    time_budget_seconds: 15,
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
    // Generation runs on one of the user's own datasets, so it is listed.
    const dataset = useDatasetStore.getState().getDatasetById(datasetId);

    set((state) => ({
      isGenerating: true,
      error: null,
      schedules: [
        {
          schedule_id: tempId,
          schedule_name: name,
          created_at: new Date().toISOString(),
          created_by_user_name: useAuthStore.getState().user?.name || "You",
          algorithm: params.algorithm === "annealing" ? "Annealing" : "DSATUR",
          parameters: params,
          status: "Running",
          dataset_id: datasetId,
          dataset: {
            name: dataset?.dataset_name ?? "",
            uploaded_at: dataset?.created_at ?? "",
            deleted: false,
            courses: dataset?.files.courses?.unique_crns ?? null,
            students: dataset?.files.enrollments?.unique_students ?? null,
            rooms: dataset?.files.rooms?.unique_rooms ?? null,
          },
          total_exams: 0,
          late_add_count: 0,
          based_on_name: null,
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

  lateAddSave: async (scheduleId, body) => {
    const result = await apiClient.schedules.lateAddSave(scheduleId, body);
    set((state) => {
      // Same dataset as the base, so the base's listed counts carry over.
      const base = state.schedules.find((s) => s.schedule_id === scheduleId);
      const item: ScheduleListItem = {
        schedule_id: result.schedule_id,
        schedule_name: result.schedule_name,
        created_at: result.created_at ?? new Date().toISOString(),
        algorithm: result.algorithm ?? LATE_ADD_ALGORITHM,
        parameters: result.parameters,
        status: result.status ?? "Completed",
        dataset_id: result.dataset_id,
        dataset: base?.dataset ?? {
          name: result.dataset_name,
          uploaded_at: result.dataset_uploaded_at ?? "",
          deleted: result.dataset_deleted ?? false,
          courses: null,
          students: null,
          rooms: null,
        },
        total_exams: result.schedule.total_exams,
        is_owner: result.is_owner,
        is_shared: result.is_shared,
        created_by_user_id: result.created_by_user_id,
        created_by_user_name: result.created_by_user_name,
        shared_by_user_id: result.shared_by_user_id,
        shared_by_user_name: result.shared_by_user_name,
        late_add_count: result.lineage?.late_additions.length ?? 0,
        based_on_name: result.lineage?.based_on?.name ?? null,
      };
      return {
        schedules: [item, ...state.schedules],
        currentSchedule: result,
      };
    });
    return result;
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
