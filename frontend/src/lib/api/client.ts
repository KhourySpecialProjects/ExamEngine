export interface BaseFileMetadata {
  filename: string;
  rows: number;
  columns: string[];
  size_bytes: number;
}

export interface CoursesFileMetadata extends BaseFileMetadata {
  unique_crns: number;
  total_students: number;
  avg_class_size: number;
  subjects: number;
}

export interface EnrollmentsFileMetadata extends BaseFileMetadata {
  unique_students: number;
  unique_crns: number;
  total_enrollments: number;
}

export interface RoomsFileMetadata extends BaseFileMetadata {
  unique_rooms: number;
  total_capacity: number;
  avg_capacity: number;
  max_capacity: number;
}

export interface DatasetMetadata {
  dataset_id: string;
  dataset_name: string;
  created_at: string;
  files: {
    courses: CoursesFileMetadata;
    enrollments: EnrollmentsFileMetadata;
    rooms: RoomsFileMetadata;
  };
  status: string;
}
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

export class ApiClient {
  private baseUrl: string;

  constructor(
    baseUrl: string = process.env.NEXT_PUBLIC_API_URL ||
      "http://localhost:8000",
  ) {
    this.baseUrl = baseUrl;
  }

  async uploadDataset(
    datasetName: string,
    files: {
      courses: File;
      enrollments: File;
      rooms: File;
    },
  ): Promise<DatasetMetadata> {
    const formData = new FormData();
    formData.append("courses", files.courses);
    formData.append("enrollments", files.enrollments);
    formData.append("rooms", files.rooms);

    if (datasetName?.trim()) {
      formData.append("dataset_name", datasetName.trim());
    }

    const response = await fetch(`${this.baseUrl}/datasets/upload`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        detail: { message: "Upload failed", errors: {} },
      }));
      throw new Error(JSON.stringify(error.detail || error));
    }

    return response.json();
  }

  async listDatasets(): Promise<DatasetMetadata[]> {
    const response = await fetch(`${this.baseUrl}/datasets`);

    if (!response.ok) {
      throw new Error("Failed to fetch datasets");
    }

    return response.json();
  }

  async getDataset(datasetId: string): Promise<DatasetMetadata> {
    const response = await fetch(`${this.baseUrl}/datasets/${datasetId}`);

    if (!response.ok) {
      throw new Error("Dataset not found");
    }

    return response.json();
  }

  async deleteDataset(datasetId: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/datasets/${datasetId}`, {
      method: "DELETE",
    });

    if (!response.ok) {
      throw new Error("Failed to delete dataset");
    }
  }
  async generateSchedule(
    datasetId: string,
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

    const url = `${this.baseUrl}/schedule/generate/${datasetId}${queryParams.toString() ? `?${queryParams}` : ""
      }`;

    const response = await fetch(url, {
      method: "POST",
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        detail: "Schedule generation failed",
      }));
      throw new Error(error.detail || "Failed to generate schedule");
    }

    return response.json();
  }
}

export const apiClient = new ApiClient();
