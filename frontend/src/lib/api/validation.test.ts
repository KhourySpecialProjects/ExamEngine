import { afterEach, describe, expect, it, vi } from "vitest";
import { ValidationAPI, type ValidationEvent } from "./validation";

function streamOf(chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
      controller.close();
    },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("ValidationAPI.runValidation", () => {
  it("emits lines split across chunks and a final line without a newline", async () => {
    vi.spyOn(console, "log").mockImplementation(() => {});
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        new Response(
          streamOf([
            '{"type":"start","check_id":"rooms.capa',
            'city"}\n\n{"type":"result","check_id":"rooms.capacity",',
            '"status":"pass","summary":"ok","count":0,"examples":[]}\n',
            '{"type":"done","counts":{"pass":1,"warn":0,"fail":0,"skipped":0},',
            '"duration_ms":5}',
          ]),
          { status: 200, headers: { "Content-Type": "application/x-ndjson" } },
        ),
      );
    vi.stubGlobal("fetch", fetchMock);
    const events: ValidationEvent[] = [];

    await new ValidationAPI("http://api.test").runValidation("s1", (event) =>
      events.push(event),
    );

    expect(events.map((event) => event.type)).toEqual([
      "start",
      "result",
      "done",
    ]);
    expect(events[0]).toEqual({ type: "start", check_id: "rooms.capacity" });
    expect(events[2]).toMatchObject({ duration_ms: 5 });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test/validation/schedules/s1",
      expect.objectContaining({ method: "POST", credentials: "include" }),
    );
  });
});
