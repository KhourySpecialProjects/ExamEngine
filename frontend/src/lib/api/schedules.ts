import { BaseAPI } from "./base";

export interface ScheduleParameters {
  max_per_day?: number;
  avoid_back_to_back?: boolean;
  max_days?: number;
}

export interface ConflictBreakdown {
  student_id: string;
  day: string;
  conflict_type: string;
  blocks: number[];
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
}

export interface CalendarExam {
  CRN: string;
  Course: string;
  Room: string;
  Capacity: number;
  Size: number;
  Valid: boolean;
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

export class SchedulesAPI extends BaseAPI {
  async generate(
    dataset_id: string,
    parameters: ScheduleParameters = {},
  ): Promise<ScheduleResult> {
    const queryParams = new URLSearchParams();

    if (parameters.max_per_day !== undefined) {
      queryParams.append("max_per_day", parameters.max_per_day.toString());
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

  async downloadOutput(files: {
    census: File;
    enrollment: File;
    classrooms: File;
  }): Promise<Blob> {
    const formData = new FormData();
    formData.append("census", files.census);
    formData.append("enrollment", files.enrollment);
    formData.append("classrooms", files.classrooms);

    const response = await fetch(`${this.baseUrl} / schedule / output`, {
      method: "POST",
      body: formData,
      credentials: "include",
    });

    if (!response.ok) throw new Error("Download failed");
    return response.blob();
  }
}

// ==================== Main API Client ====================
