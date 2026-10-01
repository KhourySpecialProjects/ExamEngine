import { afterEach, describe, expect, it, vi } from "vitest";
import { BaseAPI } from "./base";

class TestAPI extends BaseAPI {
  post(endpoint: string) {
    return this.request(endpoint, { method: "POST" });
  }
}

function failWith(status: number, body: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: false,
      status,
      statusText: "",
      json: async () => body,
    }),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("BaseAPI failed responses", () => {
  it("logs status, method, URL and the detail text, and throws the detail", async () => {
    const consoleError = vi
      .spyOn(console, "error")
      .mockImplementation(() => {});
    vi.spyOn(console, "log").mockImplementation(() => {});
    failWith(401, { detail: "Incorrect username or password" });

    await expect(
      new TestAPI("http://api.test").post("/auth/login"),
    ).rejects.toThrow("Incorrect username or password");
    expect(consoleError).toHaveBeenCalledWith(
      "[API Error] 401 POST http://api.test/auth/login: Incorrect username or password",
    );
  });

  it("lists every field of a 422 validation error", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    vi.spyOn(console, "log").mockImplementation(() => {});
    failWith(422, {
      detail: [
        {
          loc: ["query", "blocks_per_day"],
          msg: "Input should be less than or equal to 5",
        },
        { loc: ["query", "max_days"], msg: "Input should be a valid integer" },
      ],
    });

    await expect(new TestAPI("http://api.test").post("/x")).rejects.toThrow(
      "Validation error: query.blocks_per_day: Input should be less than or equal to 5; " +
        "query.max_days: Input should be a valid integer",
    );
  });
});
