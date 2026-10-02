import { BaseAPI } from "./base";

export type ValidationCategory =
  | "coverage"
  | "rooms"
  | "groups"
  | "conflicts"
  | "data";

export interface ValidationCheck {
  id: string;
  title: string;
  description: string;
  category: ValidationCategory;
}

/** Outcome of a finished check. */
export type ValidationStatus = "pass" | "warn" | "fail" | "skipped";

export interface ValidationResult {
  type: "result";
  check_id: string;
  status: ValidationStatus;
  summary: string;
  /** Offending items; may exceed `examples.length`. */
  count: number;
  examples: string[];
}

/** One line of the `POST /validation/schedules/{id}` NDJSON stream. */
export type ValidationEvent =
  | { type: "start"; check_id: string }
  | ValidationResult
  | {
      type: "done";
      counts: Record<ValidationStatus, number>;
      duration_ms: number;
    }
  | { type: "error"; message: string };

export class ValidationAPI extends BaseAPI {
  /** Every check, in run order. */
  async getChecks(): Promise<ValidationCheck[]> {
    const response = await this.request<{ checks: ValidationCheck[] }>(
      "/validation/checks",
      { method: "GET" },
    );
    return response.checks;
  }

  /** Streams the run, calling `onEvent` per event; resolves when the stream ends. */
  async runValidation(
    scheduleId: string,
    onEvent: (event: ValidationEvent) => void,
    signal?: AbortSignal,
  ): Promise<void> {
    await this.request(
      `/validation/schedules/${scheduleId}`,
      { method: "POST", signal },
      async (response) => {
        if (!response.body) throw new Error("Validation response has no body");
        await readNdjson(response.body, (line) =>
          onEvent(JSON.parse(line) as ValidationEvent),
        );
      },
    );
  }
}

/** Calls `onLine` for each non-empty line, including a final unterminated one. */
export async function readNdjson(
  body: ReadableStream<Uint8Array>,
  onLine: (line: string) => void,
): Promise<void> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffered = "";
  const flush = (text: string) => {
    if (text.trim()) onLine(text);
  };
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffered += decoder.decode(value, { stream: true });
      const lines = buffered.split("\n");
      buffered = lines.pop() ?? "";
      lines.forEach(flush);
    }
    flush(buffered + decoder.decode());
  } catch (error) {
    // Close the connection, e.g. when a line fails to parse.
    reader.cancel().catch(() => {});
    throw error;
  }
}
