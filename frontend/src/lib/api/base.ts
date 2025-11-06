export class BaseAPI {
  protected baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  protected async request<T>(
    endpoint: string,
    options: RequestInit = {},
  ): Promise<T> {
    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        ...options,
        credentials: "include", // Always include cookies
      });

      if (!response.ok) {
        const error = await response
          .json()
          .catch(() => ({ detail: "Request failed" }));
        throw new Error(JSON.stringify(error.detail || error));
      }

      if (response.status === 204) return {} as T;
      return response.json();
    } catch (error) {
      // Enhanced error logging for debugging
      if (error instanceof TypeError && error.message.includes("fetch")) {
        console.error("❌ Network error - Backend unreachable");
        console.error("   Attempted URL:", `${this.baseUrl}${endpoint}`);
        console.error("   Error:", error);
        console.error("   Troubleshooting:");
        console.error("   - Is the backend container running? (docker ps)");
        console.error(
          "   - Check backend logs: docker logs exam_engine_backend",
        );
        console.error("   - Test from host: curl http://localhost:8000/docs");
        console.error(
          "   - Test from frontend container: docker exec exam_engine_frontend curl http://backend:8000/docs",
        );
        throw new Error(
          `Failed to connect to backend at ${this.baseUrl}. Is the server running? Check console for details.`,
        );
      }
      throw error;
    }
  }
}
