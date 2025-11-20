import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

import { ExamListDialog } from "./ExamListDialog";

// ---- Mock Calendar Store ----
vi.mock("@/lib/store/calendarStore", () => {
  return {
    useCalendarStore: vi.fn(),
  };
});

// ---- Mock ExamList ----
vi.mock("./ExamList", () => ({
  ExamList: ({ exams }: any) => (
    <div data-testid="exam-list">{JSON.stringify(exams)}</div>
  ),
}));

let useCalendarStore: any;
beforeEach(async () => {
  const mockedModule = await vi.importMock("@/lib/store/calendarStore");
  useCalendarStore = mockedModule.useCalendarStore;
});

describe("ExamListDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns null when selectedCell is null", () => {
    const mockSelectCell = vi.fn();

    // Mock the hook return value
    (useCalendarStore as any).mockReturnValue({
      selectedCell: null,
      selectCell: mockSelectCell,
    });

    const { container } = render(<ExamListDialog />);

    expect(container.firstChild).toBeNull();
  });

  it("renders dialog when a cell is selected", () => {
    useCalendarStore.mockReturnValue({
      selectedCell: {
        day: "Monday",
        timeSlot: "9:00 AM",
        examCount: 2,
        exams: [],
      },
      selectCell: vi.fn(),
    });

    render(<ExamListDialog />);

    // Title rendering
    expect(
      screen.getByText("Monday - 9:00 AM")
    ).not.toBeUndefined();

    // Description
    expect(
      screen.getByText("2 exams scheduled")
    ).not.toBeUndefined();
  });

  it("calls selectCell(null) when dialog closes", () => {
    const mockSelectCell = vi.fn();

    useCalendarStore.mockReturnValue({
      selectedCell: {
        day: "Monday",
        timeSlot: "9:00 AM",
        examCount: 1,
        exams: [],
      },
      selectCell: mockSelectCell,
    });

    render(<ExamListDialog />);

    const dialog = screen.getByRole("dialog");

    // Trigger Radix `onOpenChange(false)`
    fireEvent.keyDown(dialog, { key: "Escape" });

    expect(mockSelectCell).toHaveBeenCalledWith(null);
  });

  it("passes exam list to ExamList component", () => {
    const mockExams = [{ id: 1, title: "Math Exam" }];

    useCalendarStore.mockReturnValue({
      selectedCell: {
        day: "Tuesday",
        timeSlot: "11:00 AM",
        examCount: 1,
        exams: mockExams,
      },
      selectCell: vi.fn(),
    });

    render(<ExamListDialog />);

    const examList = screen.getByTestId("exam-list");
    expect(examList.textContent).toContain("Math Exam");
  });
});
