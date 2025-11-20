import { BaseAPI } from "./base";

export interface ScheduleParameters {
  student_max_per_day?: number;
  instructor_max_per_day?: number;
  avoid_back_to_back?: boolean;
  max_days?: number;
  prioritize_large_courses?: boolean;
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
  schedule_name: string;
  summary: ScheduleSummary;
  conflicts: ScheduleConflicts;
  failures: ScheduleFailure[];
  schedule: ScheduleData;
  parameters: ScheduleParameters;
  is_owner?: boolean;
  is_shared?: boolean;
  created_by_user_id?: string;
  created_by_user_name?: string;
  shared_by_user_id?: string | null;
  shared_by_user_name?: string | null;
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
  is_shared?: boolean; // Whether this schedule is shared with the user
  is_owner?: boolean; // Whether the user owns this schedule
  created_by_user_id?: string;
  created_by_user_name?: string;
  shared_by_user_id?: string | null;
  shared_by_user_name?: string | null;
}

export interface ScheduleShare {
  share_id: string;
  schedule_id: string;
  shared_with_user_id: string;
  shared_with_user_name: string;
  shared_with_user_email: string;
  permission: "view" | "edit";
  shared_by_user_id: string;
  shared_at: string;
}

export interface SharedSchedule {
  share_id: string;
  schedule_id: string;
  schedule_name: string;
  permission: "view" | "edit";
  shared_by_user_id: string;
  shared_by_user_name: string;
  shared_at: string;
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
    if (parameters.prioritize_large_courses !== undefined) {
      queryParams.append(
        "prioritize_large_courses",
        parameters.prioritize_large_courses.toString(),
      );
    }
    return this.request(
      `/schedule/generate/${dataset_id}${queryParams.toString() ? `?${queryParams}` : ""}`,
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
  async get(id: string): Promise<ScheduleResult> {
    return this.request(`/schedule/${id}`, {
      method: "GET",
    });
  }

  async shareSchedule(
    scheduleId: string,
    userId: string,
    permission: "view" | "edit",
  ): Promise<{ message: string; share_id: string }> {
    return this.request(`/schedule/${scheduleId}/share`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId, permission }),
    });
  }

  async getScheduleShares(scheduleId: string): Promise<ScheduleShare[]> {
    return this.request(`/schedule/${scheduleId}/shares`, {
      method: "GET",
    });
  }

  async unshareSchedule(shareId: string): Promise<{ message: string }> {
    return this.request(`/schedule/shares/${shareId}`, {
      method: "DELETE",
    });
  }

  async getSharedSchedules(): Promise<SharedSchedule[]> {
    return this.request("/schedule/shared", {
      method: "GET",
    });
  }
}
