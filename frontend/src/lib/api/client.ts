import { AdminAPI } from "./admin";
import { AuthAPI } from "./auth";
import { DatasetsAPI } from "./datasets";
import { SchedulesAPI } from "./schedules";

/**
 * Get the appropriate API base URL based on execution context
 * - Server-side (Docker): Use Docker service name
 * - Client-side (Browser): Use localhost or configured URL
 */
function getApiBaseUrl(): string {
  // If explicitly set, use that
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }

  // Check if we're running server-side (Node.js environment)
  if (typeof window === "undefined") {
    // Server-side: Use Docker service name if available, otherwise localhost
    return process.env.API_URL || "http://backend:8000";
  }

  // Client-side: Use localhost (browser can access host's localhost via port mapping)
  return "http://localhost:8000";
}

class ApiClient {
  public auth: AuthAPI;
  public datasets: DatasetsAPI;
  public schedules: SchedulesAPI;
  public baseUrl: string;
  public admin: AdminAPI;

  constructor(baseUrl?: string) {
    this.baseUrl = baseUrl || getApiBaseUrl();
    this.auth = new AuthAPI(this.baseUrl);
    this.datasets = new DatasetsAPI(this.baseUrl);
    this.schedules = new SchedulesAPI(this.baseUrl);
    this.admin = new AdminAPI(this.baseUrl);

    // Log the URL being used (only in development)
    if (process.env.NODE_ENV === "development") {
      console.log(`[API Client] Using base URL: ${this.baseUrl}`);
    }
  }
}

export const apiClient = new ApiClient();
