import type {
  CommonExamValidation,
  DatasetMetadata,
} from "../types/datasets.api.types";
import { BaseAPI } from "./base";

export class DatasetsAPI extends BaseAPI {
  async list(): Promise<DatasetMetadata[]> {
    return this.request("/datasets");
  }

  async deleteDataset(datasetId: string): Promise<void> {
    return this.request(`/datasets/${datasetId}`, { method: "DELETE" });
  }

  async upload(
    datasetName: string,
    files: {
      courses: File;
      enrollments: File;
      rooms: File;
      room_blockouts?: File;
      combined_exams?: File;
      common_exams?: File;
    },
  ): Promise<DatasetMetadata> {
    const formData = new FormData();
    formData.append("courses", files.courses);
    formData.append("enrollments", files.enrollments);
    formData.append("rooms", files.rooms);
    if (files.room_blockouts) {
      formData.append("room_blockouts", files.room_blockouts);
    }
    if (files.combined_exams) {
      formData.append("combined_exams", files.combined_exams);
    }
    if (files.common_exams) {
      formData.append("common_exams", files.common_exams);
    }
    if (datasetName?.trim()) {
      formData.append("dataset_name", datasetName.trim());
    }

    return this.request("/datasets/upload", {
      method: "POST",
      body: formData,
    });
  }

  async deleteById(
    datasetId: string,
  ): Promise<{ message: string; dataset_id: string }> {
    return this.request(`/datasets/${datasetId}`, { method: "DELETE" });
  }

  async getCourseMerges(datasetId: string): Promise<Record<string, string[]>> {
    return this.request(`/datasets/${datasetId}/merges`);
  }

  async validateCourseMerge(
    datasetId: string,
    crns: string[],
  ): Promise<{
    is_valid: boolean;
    has_suitable_room?: boolean;
    message: string;
    warning_type?: string;
    total_enrollment?: number;
    max_room_capacity?: number;
  }> {
    return this.request(`/datasets/${datasetId}/merges/validate`, {
      method: "POST",
      body: JSON.stringify({ crns: crns }),
    });
  }

  async setCourseMerges(
    datasetId: string,
    merges: Record<string, string[]>,
  ): Promise<{
    message: string;
    validation: Record<string, { is_valid: boolean; warning_type?: string }>;
  }> {
    return this.request(`/datasets/${datasetId}/merges`, {
      method: "POST",
      body: JSON.stringify({ merges }),
    });
  }

  async clearCourseMerges(datasetId: string): Promise<{ message: string }> {
    return this.request(`/datasets/${datasetId}/merges`, {
      method: "DELETE",
    });
  }

  async getCommonExams(datasetId: string): Promise<Record<string, string[]>> {
    return this.request(`/datasets/${datasetId}/common-exams`);
  }

  async validateCommonExam(
    datasetId: string,
    crns: string[],
  ): Promise<CommonExamValidation> {
    return this.request(`/datasets/${datasetId}/common-exams/validate`, {
      method: "POST",
      body: JSON.stringify({ crns }),
    });
  }

  async setCommonExams(
    datasetId: string,
    groups: Record<string, string[]>,
  ): Promise<{ message: string; validation?: Record<string, unknown> }> {
    return this.request(`/datasets/${datasetId}/common-exams`, {
      method: "POST",
      body: JSON.stringify({ common_exams: groups }),
    });
  }

  async clearCommonExams(datasetId: string): Promise<{ message: string }> {
    return this.request(`/datasets/${datasetId}/common-exams`, {
      method: "DELETE",
    });
  }
}
