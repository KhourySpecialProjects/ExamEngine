import { BaseAPI } from "./base";

interface GenerateScheduleResponse {
  summary: {
    num_classes: number;
    num_students: number;
    potential_overlaps: number;
    real_conflicts: number;
    num_rooms: number;
    slots_used: number;
  };
  preview: Array<{
    CRN: number;
    Course: string;
    Day: string;
    Block: string;
    Room: string;
    Capacity: number;
    Size: number;
    Valid: boolean;
  }>;
}

export class SchedulesAPI extends BaseAPI {
  async generate(files: {
    census: File;
    enrollment: File;
    classrooms: File;
  }): Promise<GenerateScheduleResponse> {
    const formData = new FormData();
    formData.append("census", files.census);
    formData.append("enrollment", files.enrollment);
    formData.append("classrooms", files.classrooms);

    return this.request("/schedule/generate", {
      method: "POST",
      body: formData,
    });
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

    const response = await fetch(`${this.baseUrl}/schedule/output`, {
      method: "POST",
      body: formData,
      credentials: "include",
    });

    if (!response.ok) throw new Error("Download failed");
    return response.blob();
  }
}

// ==================== Main API Client ====================
