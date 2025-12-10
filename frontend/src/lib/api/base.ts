export class BaseAPI {
  protected baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  protected async request<T>(
    endpoint: string,
    options: RequestInit = {},
  ): Promise<T> {
    const fullUrl = `${this.baseUrl}${endpoint}`;
    console.log(`[API Request] ${options.method || "GET"} ${fullUrl}`);
    
    try {
      // Prepare headers - ensure Content-Type is set for JSON requests
      let finalHeaders: HeadersInit | undefined = undefined;
      
      // Always create a Headers object to ensure proper handling
      const headers = new Headers();
      
      // Copy existing headers first (if provided)
      if (options.headers) {
        if (options.headers instanceof Headers) {
          options.headers.forEach((value, key) => {
            headers.set(key, value);
          });
        } else if (typeof options.headers === 'object') {
          Object.entries(options.headers).forEach(([key, value]) => {
            if (typeof value === 'string') {
              headers.set(key, value);
            }
          });
        }
      }
      
      // For JSON string bodies, ensure Content-Type is set
      if (options.body && typeof options.body === 'string') {
        // Only set Content-Type if not already explicitly set
        if (!headers.has('Content-Type') && !headers.has('content-type')) {
          headers.set('Content-Type', 'application/json');
        }
        finalHeaders = headers;
      } else if (headers.has('Content-Type') || headers.has('content-type')) {
        // If headers were provided, use them
        finalHeaders = headers;
      } else {
        // Otherwise use original headers or undefined
        finalHeaders = options.headers as HeadersInit | undefined;
      }
      
      // Prepare request options with headers set correctly
      const requestOptions: RequestInit = {
        method: options.method,
        headers: finalHeaders,
        body: options.body,
        credentials: "include", // Always include cookies
      };
      
      // Debug logging before request
      if (options.method === "POST" && options.body) {
        console.log(`[API Request] POST ${fullUrl}`);
        console.log(`[API Request] Headers:`, finalHeaders);
        console.log(`[API Request] Body:`, options.body);
      }
      
      const response = await fetch(fullUrl, requestOptions);

      console.log(`[API Response] ${response.status} ${response.statusText} for ${fullUrl}`);

      if (!response.ok) {
        const error = await response
          .json()
          .catch(() => ({ detail: `Request failed with status ${response.status}` }));
        console.error(`[API Error]`, error);
        
        // Handle validation errors (422) - extract detail from nested structure
        if (response.status === 422 && error.detail) {
          // Pydantic validation errors are in error.detail array
          if (Array.isArray(error.detail)) {
            const errorMessages = error.detail.map((e: any) => {
              const field = e.loc ? e.loc.join('.') : 'field';
              return `${field}: ${e.msg}`;
            }).join('; ');
            throw new Error(`Validation error: ${errorMessages}`);
          }
          // If detail is a string
          if (typeof error.detail === 'string') {
            throw new Error(error.detail);
          }
        }
        
        throw new Error(error.detail || error.message || JSON.stringify(error));
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
