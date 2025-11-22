import { BaseAPI } from "./base";
import type { DatasetMetadata } from "../types/datasets.api.types";

export class DatasetsAPI extends BaseAPI {
  async list(): Promise<DatasetMetadata[]> {
    return this.request("/datasets");
  }

  async deleteDataset(datasetId: string): Promise<void> {
    return this.request(`/datasets/${datasetId}`, { method: "DELETE" });
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
}
