import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ValidationCheck, ValidationEvent } from "@/lib/api/validation";
import { ValidateScheduleDialog } from "./ValidateScheduleDialog";

vi.mock("sonner", () => ({
  toast: { error: vi.fn() },
}));

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    validation: { getChecks: vi.fn(), runValidation: vi.fn() },
  },
}));

import { toast } from "sonner";
import { apiClient } from "@/lib/api/client";

const getChecks = vi.mocked(apiClient.validation.getChecks);
const runValidation = vi.mocked(apiClient.validation.runValidation);

const CHECKS: ValidationCheck[] = [
  ["coverage.crn_single_row", "coverage"],
  ["rooms.capacity", "rooms"],
  ["groups.common_same_slot", "groups"],
  ["conflicts.student_double_book", "conflicts"],
  ["data.duplicates", "data"],
].map(([id, category]) => ({
  id,
  title: `Title ${id}`,
  description: `Description ${id}`,
  category: category as ValidationCheck["category"],
}));

/** Starts a run whose events the test emits by hand. */
async function startRun() {
  const run = Promise.withResolvers<void>();
  let emit: (event: ValidationEvent) => void = () => {};
  let signal: AbortSignal | undefined;
  runValidation.mockImplementation((_id, onEvent, abortSignal) => {
    emit = onEvent;
    signal = abortSignal;
    return run.promise;
  });

  render(<ValidateScheduleDialog scheduleId="s1" scheduleName="Fall" />);
  fireEvent.click(screen.getByRole("button", { name: "Validate Schedule" }));
  fireEvent.click(
    await screen.findByRole("button", { name: "Run Validation" }),
  );
  expect(runValidation).toHaveBeenCalledWith(
    "s1",
    expect.any(Function),
    expect.any(AbortSignal),
  );

  return {
    emit: (event: ValidationEvent) => act(() => emit(event)),
    resolve: () => act(async () => run.resolve()),
    reject: (error: Error) => act(async () => run.reject(error)),
    signal: () => signal,
  };
}

function row(id: string) {
  return screen.getByTestId(`check-${id}`);
}

function result(
  check_id: string,
  status: "pass" | "warn" | "fail" | "skipped",
  extra: Partial<{ summary: string; count: number; examples: string[] }> = {},
): ValidationEvent {
  return {
    type: "result",
    check_id,
    status,
    summary: `${status} summary`,
    count: 0,
    examples: [],
    ...extra,
  };
}

describe("ValidateScheduleDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getChecks.mockResolvedValue(CHECKS);
  });

  it("shows every check as pending, grouped by category, before running", async () => {
    render(<ValidateScheduleDialog scheduleId="s1" />);
    fireEvent.click(screen.getByRole("button", { name: "Validate Schedule" }));

    await screen.findByRole("button", { name: "Run Validation" });
    for (const heading of [
      "Coverage",
      "Rooms",
      "Combined & common groups",
      "Conflicts",
      "Data consistency",
    ]) {
      expect(screen.getByRole("heading", { name: heading })).toBeTruthy();
    }
    for (const check of CHECKS) {
      expect(row(check.id).dataset.status).toBe("pending");
    }
    expect(runValidation).not.toHaveBeenCalled();
  });

  it("shows a check's description only from its info button", async () => {
    render(<ValidateScheduleDialog scheduleId="s1" />);
    fireEvent.click(screen.getByRole("button", { name: "Validate Schedule" }));
    await screen.findByRole("button", { name: "Run Validation" });

    expect(screen.queryByText("Description rooms.capacity")).toBeNull();

    fireEvent.click(
      screen.getByRole("button", { name: "About: Title rooms.capacity" }),
    );

    expect(await screen.findByText("Description rooms.capacity")).toBeTruthy();
  });

  it("reports a failed catalog load inline", async () => {
    getChecks.mockRejectedValue(new Error("Not authenticated"));

    render(<ValidateScheduleDialog scheduleId="s1" />);
    fireEvent.click(screen.getByRole("button", { name: "Validate Schedule" }));

    expect(
      await screen.findByText("Failed to load checks: Not authenticated"),
    ).toBeTruthy();
  });

  it("renders streamed progress, results and totals", async () => {
    const run = await startRun();
    expect(screen.getByRole("button", { name: "Running…" })).toHaveProperty(
      "disabled",
      true,
    );

    run.emit({ type: "start", check_id: "coverage.crn_single_row" });
    expect(row("coverage.crn_single_row").dataset.status).toBe("running");
    expect(row("rooms.capacity").dataset.status).toBe("pending");

    run.emit(result("coverage.crn_single_row", "pass"));
    run.emit(
      result("rooms.capacity", "fail", {
        summary: "2 exams exceed room capacity.",
        count: 23,
        examples: ["CRN 101 in Room A", "CRN 202 in Room B"],
      }),
    );
    run.emit(result("groups.common_same_slot", "warn", { count: 1 }));
    run.emit(result("conflicts.student_double_book", "skipped"));
    run.emit(result("data.duplicates", "pass"));

    const expectations = {
      "coverage.crn_single_row": ["pass", "text-green-600"],
      "rooms.capacity": ["fail", "text-red-600"],
      "groups.common_same_slot": ["warn", "text-amber-600"],
      "conflicts.student_double_book": ["skipped", "text-amber-600"],
    } as const;
    for (const [id, [status, colour]] of Object.entries(expectations)) {
      expect(row(id).dataset.status).toBe(status);
      expect(row(id).className).toContain(colour);
    }

    expect(screen.getByText("2 exams exceed room capacity.")).toBeTruthy();
    expect(screen.getByText("CRN 202 in Room B")).toBeTruthy();
    expect(screen.getByText("and 21 more")).toBeTruthy();
    expect(screen.getByText("warn summary")).toBeTruthy();
    expect(screen.getByText("Skipped")).toBeTruthy();

    run.emit({
      type: "done",
      counts: { pass: 2, warn: 1, fail: 1, skipped: 1 },
      duration_ms: 1234,
    });
    await run.resolve();

    expect(
      screen.getByText(
        "5 checks · 2 passed · 1 warning · 1 failed · 1 skipped",
      ),
    ).toBeTruthy();
    expect(toast.error).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Run Again" }));
    for (const check of CHECKS) {
      expect(row(check.id).dataset.status).toBe("pending");
    }
  });

  it("shows a failed run and returns its running checks to pending", async () => {
    const run = await startRun();
    run.emit({ type: "start", check_id: "coverage.crn_single_row" });
    run.emit(result("coverage.crn_single_row", "pass"));
    run.emit({ type: "start", check_id: "rooms.capacity" });

    await run.reject(new Error("Schedule not found"));

    expect(
      screen.getByText("Validation failed: Schedule not found"),
    ).toBeTruthy();
    expect(toast.error).toHaveBeenCalledWith("Validation failed", {
      description: "Schedule not found",
    });
    expect(row("rooms.capacity").dataset.status).toBe("pending");
    expect(row("coverage.crn_single_row").dataset.status).toBe("pass");
    expect(screen.getByRole("button", { name: "Run Again" })).toHaveProperty(
      "disabled",
      false,
    );
  });

  it("treats an error event as a failed run", async () => {
    const run = await startRun();
    run.emit({ type: "start", check_id: "coverage.crn_single_row" });
    run.emit({ type: "error", message: "Dataset files unavailable" });
    await run.resolve();

    expect(
      screen.getByText("Validation failed: Dataset files unavailable"),
    ).toBeTruthy();
    expect(row("coverage.crn_single_row").dataset.status).toBe("pending");
  });

  it("aborts an in-flight run when the dialog closes", async () => {
    const run = await startRun();
    expect(run.signal()?.aborted).toBe(false);

    fireEvent.click(screen.getByRole("button", { name: "Close" }));

    expect(run.signal()?.aborted).toBe(true);
  });
});
