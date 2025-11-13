import { BaseAPI } from "./base";

export interface ScheduleParameters {
  student_max_per_day?: number;
  instructor_max_per_day?: number;
  avoid_back_to_back?: boolean;
  max_days?: number;
}

export interface ConflictBreakdown {
  student_id?: string;
  entity_id?: string;
  day: string;
  block?: number;
  block_time?: string;
  conflict_type: string;
  blocks?: number[];
  crn?: string;
  course?: string;
  conflicting_crn?: string;
  conflicting_course?: string;
  conflicting_crns?: string[];
  conflicting_courses?: string[];
}

export interface ScheduleFailure {
  CRN: string;
  Course: string;
  Size: number;
  reasons: Record<string, number>;
}

export interface ScheduleExam {
  CRN: string;
  Course: string;
  Day: string;
  Block: string;
  Room: string;
  Capacity: number;
  Size: number;
  Valid: boolean;
  Instructor?: string;
}

export interface CalendarExam {
  CRN: string;
  Course: string;
  Room: string;
  Capacity: number;
  Size: number;
  Valid: boolean;
  Instructor?: string;
}

export interface CalendarData {
  [day: string]: {
    [timeSlot: string]: CalendarExam[];
  };
}

export interface ScheduleSummary {
  num_classes: number;
  num_students: number;
  potential_overlaps: number;
  real_conflicts: number;
  num_rooms: number;
  slots_used: number;
}

export interface ScheduleConflicts {
  total: number;
  breakdown: ConflictBreakdown[];
  details: Record<string, string[]>;
}

export interface ScheduleData {
  complete: ScheduleExam[];
  calendar: CalendarData;
  total_exams: number;
}

export interface ScheduleResult {
  dataset_id: string;
  dataset_name: string;
  summary: ScheduleSummary;
  conflicts: ScheduleConflicts;
  failures: ScheduleFailure[];
  schedule: ScheduleData;
  parameters: ScheduleParameters;
}

export interface ScheduleListItem {
  schedule_id: string;
  schedule_name: string;
  created_at: string;
  algorithm: string;
  parameters: ScheduleParameters;
  status: "Running" | "Completed" | "Failed";
  dataset_id: string;
  total_exams: number;
}

export class SchedulesAPI extends BaseAPI {
  async generate(
    dataset_id: string,
    schedule_name: string,
    parameters: ScheduleParameters = {},
  ): Promise<ScheduleResult> {
    const queryParams = new URLSearchParams();

    if (schedule_name) {
      queryParams.append("schedule_name", schedule_name);
    }

    if (parameters.student_max_per_day !== undefined) {
      queryParams.append(
        "student_max_per_day",
        parameters.student_max_per_day.toString(),
      );
    }
    if (parameters.instructor_max_per_day !== undefined) {
      queryParams.append(
        "instructor_max_per_day",
        parameters.instructor_max_per_day.toString(),
      );
    }
    if (parameters.avoid_back_to_back !== undefined) {
      queryParams.append(
        "avoid_back_to_back",
        parameters.avoid_back_to_back.toString(),
      );
    }
    if (parameters.max_days !== undefined) {
      queryParams.append("max_days", parameters.max_days.toString());
    }
    return this.request(
      `/schedule/generate/${dataset_id}/${queryParams.toString() ? `?${queryParams}` : ""}`,
      {
        method: "POST",
      },
    );
  }
  async list(): Promise<ScheduleListItem[]> {
    return this.request("/schedule", {
      method: "GET",
    });
  }
}
