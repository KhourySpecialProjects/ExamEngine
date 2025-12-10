import { BaseAPI } from "./base";
import type { DatasetMetadata } from "../types/datasets.api.types";

export class DatasetsAPI extends BaseAPI {
  async list(): Promise<DatasetMetadata[]> {
    return this.request("/api/datasets");
  }

  async deleteDataset(datasetId: string): Promise<void> {
    return this.request(`/api/datasets/${datasetId}`, { method: "DELETE" });
  }

  async upload(
    datasetName: string,
    files: { courses: File; enrollments: File; rooms: File },
  ): Promise<DatasetMetadata> {
    const formData = new FormData();
    formData.append("courses", files.courses);
    formData.append("enrollments", files.enrollments);
    formData.append("rooms", files.rooms);
    if (datasetName?.trim()) {
      formData.append("dataset_name", datasetName.trim());
    }

    return this.request("/api/datasets/upload", {
      method: "POST",
      body: formData,
    });
  }

  async deleteById(
    datasetId: string,
  ): Promise<{ message: string; dataset_id: string }> {
    return this.request(`/api/datasets/${datasetId}`, { method: "DELETE" });
  }

  async getCourseMerges(datasetId: string): Promise<Record<string, string[]>> {
    return this.request(`/api/datasets/${datasetId}/merges`);
  }

  async validateCourseMerge(
    datasetId: string,
    crns: string[],
  ): Promise<{ is_valid: boolean; has_suitable_room?: boolean; message: string; warning_type?: string; total_enrollment?: number; max_room_capacity?: number }> {
    return this.request(`/api/datasets/${datasetId}/merges/validate`, {
      method: "POST",
      body: JSON.stringify({ crns: crns }),
    });
  }

  async setCourseMerges(
    datasetId: string,
    merges: Record<string, string[]>,
  ): Promise<{ message: string; validation: Record<string, any> }> {
    return this.request(`/api/datasets/${datasetId}/merges`, {
      method: "POST",
      body: JSON.stringify({ merges }),
    });
  }

  async clearCourseMerges(
    datasetId: string,
  ): Promise<{ message: string }> {
    return this.request(`/api/datasets/${datasetId}/merges`, {
      method: "DELETE",
    });
  }
}
