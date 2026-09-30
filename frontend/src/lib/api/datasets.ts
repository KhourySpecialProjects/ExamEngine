import type { DatasetMetadata } from "../types/datasets.api.types";
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

  async getCommonExams(datasetId: string): Promise<Record<string, string[]>> {
    return this.request(`/datasets/${datasetId}/common-exams`);
  }
}
