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
      let finalHeaders: HeadersInit | undefined;

      // Always create a Headers object to ensure proper handling
      const headers = new Headers();

      // Copy existing headers first (if provided)
      if (options.headers) {
        if (options.headers instanceof Headers) {
          options.headers.forEach((value, key) => {
            headers.set(key, value);
          });
        } else if (typeof options.headers === "object") {
          Object.entries(options.headers).forEach(([key, value]) => {
            if (typeof value === "string") {
              headers.set(key, value);
            }
          });
        }
      }

      // For JSON string bodies, ensure Content-Type is set
      if (options.body && typeof options.body === "string") {
        // Only set Content-Type if not already explicitly set
        if (!headers.has("Content-Type") && !headers.has("content-type")) {
          headers.set("Content-Type", "application/json");
        }
        finalHeaders = headers;
      } else if (headers.has("Content-Type") || headers.has("content-type")) {
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

      console.log(
        `[API Response] ${response.status} ${response.statusText} for ${fullUrl}`,
      );

      if (!response.ok) {
        const body: unknown = await response.json().catch(() => ({
          detail: `Request failed with status ${response.status}`,
        }));
        const message = errorMessage(response.status, body);
        console.error(
          `[API Error] ${response.status} ${options.method || "GET"} ${fullUrl}: ${message}`,
        );
        throw new Error(message);
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

/** Text of a failed response; callers show (and some parse) the thrown message. */
function errorMessage(status: number, body: unknown): string {
  const detail = field(body, "detail");
  // Pydantic validation errors: detail is a list of {loc, msg}
  if (status === 422 && Array.isArray(detail)) {
    const issues = detail
      .map((issue: unknown) => {
        const loc = field(issue, "loc");
        return `${Array.isArray(loc) ? loc.join(".") : "field"}: ${field(issue, "msg")}`;
      })
      .join("; ");
    return `Validation error: ${issues}`;
  }
  // Object details (e.g. {message, errors}) are passed on as JSON so callers
  // can parse them; String() would yield "[object Object]".
  if (detail && typeof detail === "object") return JSON.stringify(detail);
  if (detail) return String(detail);
  const message = field(body, "message");
  return message ? String(message) : JSON.stringify(body);
}

function field(value: unknown, key: string): unknown {
  return value && typeof value === "object"
    ? Reflect.get(value, key)
    : undefined;
}
