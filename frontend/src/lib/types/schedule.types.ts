import type {
  ScheduleListItem,
  ScheduleParameters,
  ScheduleResult,
} from "../api/schedules";

export interface SchedulesState {
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
  deleteSchedule: (scheduleId: string) => Promise<void>;
  setScheduleData: (schedule: ScheduleResult) => void;
  setScheduleName: (name: string) => void;
  setParameters: (params: Partial<ScheduleParameters>) => void;
  clearSchedule: () => void;
  clearError: () => void;
}
