import { AuthAPI } from "./auth";
import { DatasetsAPI } from "./datasets";
import { SchedulesAPI } from "./schedules";

class ApiClient {
  public auth: AuthAPI;
  public datasets: DatasetsAPI;
  public schedules: SchedulesAPI;

  constructor(
    baseUrl: string = process.env.NEXT_PUBLIC_API_URL ||
      "http://localhost:8000",
  ) {
    this.auth = new AuthAPI(baseUrl);
    this.datasets = new DatasetsAPI(baseUrl);
    this.schedules = new SchedulesAPI(baseUrl);
  }
}

export const apiClient = new ApiClient();
