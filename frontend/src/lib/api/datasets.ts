import { BaseAPI } from "./base";

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

export class DatasetsAPI extends BaseAPI {
  async list(): Promise<DatasetMetadata[]> {
    return this.request("/datasets");
  }

  async deleteDataset(datasetId: string): Promise<void> {
    return this.request(`/datasets/${datasetId}`, { method: "DELETE" });
  }

  async getById(datasetId: string): Promise<DatasetMetadata> {
    return this.request(`/datasets/${datasetId}`);
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
