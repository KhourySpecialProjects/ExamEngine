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
        console.error("Network error - check if backend is running at:", this.baseUrl);
        throw new Error(`Failed to connect to backend at ${this.baseUrl}. Is the server running?`);
      }
      throw error;
    }
  }
}
