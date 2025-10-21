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

export class ApiClient {
  private baseUrl: string;
  private token: string | null = null;

  constructor(
    baseUrl: string = process.env.NEXT_PUBLIC_API_URL ||
      "http://localhost:8000",
  ) {
    this.baseUrl = baseUrl;
  }

  setToken(token: string | null) {
    this.token = token;
  }

  private async authFetch(input: RequestInfo, init?: RequestInit) {
    const headers = new Headers(init?.headers || {});
    if (this.token) {
      headers.set("Authorization", `Bearer ${this.token}`);
    }
    return fetch(input, { ...init, headers });
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

    const response = await this.authFetch(`${this.baseUrl}/datasets/upload`, {
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
  const response = await this.authFetch(`${this.baseUrl}/datasets`);

    if (!response.ok) {
      throw new Error("Failed to fetch datasets");
    }

    return response.json();
  }

  async getDataset(datasetId: string): Promise<DatasetMetadata> {
  const response = await this.authFetch(`${this.baseUrl}/datasets/${datasetId}`);

    if (!response.ok) {
      throw new Error("Dataset not found");
    }

    return response.json();
  }

  async deleteDataset(datasetId: string): Promise<void> {
    const response = await this.authFetch(`${this.baseUrl}/datasets/${datasetId}`, {
      method: "DELETE",
    });

    if (!response.ok) {
      throw new Error("Failed to delete dataset");
    }
  }
}

export const apiClient = new ApiClient();
