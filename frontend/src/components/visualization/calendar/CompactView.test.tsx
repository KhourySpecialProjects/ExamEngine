import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, Mock } from "vitest";
import '@testing-library/jest-dom/vitest';
import CompactView from "./CompactView";

vi.mock("@/lib/hooks/useScheduleData", () => ({
  useScheduleData: vi.fn(),
}));

beforeEach(() => {
  vi.clearAllMocks(); 
});

vi.mock("@/components/common/EmptyScheduleState", () => ({
  EmptyScheduleState: ({ isLoading }: any) => (
    <div>{isLoading ? "Loading…" : "No Data"}</div>
  ),
}));

const mockSelect = vi.fn();

vi.mock("@/lib/store/calendarStore", () => {
  return {
    useCalendarStore: (fn: any) =>
      fn({
        colorTheme: "gray",
        setColorTheme: vi.fn(),
        selectCell: mockSelect, 
      }),
  };
});

// Mock Course component
vi.mock("../Course", () => ({
  Course: ({ title, students }: any) => (
    <div data-testid="course">
      {title} - {students} students
    </div>
  ),
}));

vi.mock("./CalendarGrid", () => ({
  CalendarGrid: ({ data, renderCell }: any) => (
    <div data-testid="grid">
      {data.map((row: any, i: number) =>
        row.days.map((cell: any, j: number) => (
          <div data-testid="grid-cell" key={`${i}-${j}`}>
            {renderCell(cell)}
          </div>
        ))
      )}
    </div>
  ),
}));

const { useScheduleData } = await import("@/lib/hooks/useScheduleData");
const { useCalendarStore } = await import("@/lib/store/calendarStore");

describe("CompactView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });


  it("renders empty state when no data", () => {
    (useScheduleData as Mock).mockReturnValue({
      hasData: false,
      isLoading: false,
      calendarRows: [],
    });

    render(<CompactView />);
    expect(screen.getByText("No Data")).toBeDefined();
  });


  it("renders title and subtitle when data available", () => {
    (useScheduleData as Mock).mockReturnValue({
      hasData: true,
      isLoading: false,
      calendarRows: [
        { days: [{ exams: [] }] },
      ],
    });

    render(<CompactView />);

    expect(screen.getByText("Compact View")).toBeDefined();
    expect(
      screen.getByText("Detailed view of scheduled exams with course information")
    ).toBeDefined();
  });


  it("renders up to 6 course cards", () => {
    const exams = Array.from({ length: 8 }).map((_, i) => ({
      id: i,
      courseCode: `CSE${i}`,
      studentCount: 10 + i,
      building: "A",
    }));

    (useScheduleData as Mock).mockReturnValue({
      hasData: true,
      isLoading: false,
      calendarRows: [
        { days: [{ exams }] },
      ],
    });

    render(<CompactView />);

    // Only first 6 should appear
    const courseCards = screen.getAllByTestId("course");
    expect(courseCards.length).toBe(6);
  });


  it("handles empty exam cells correctly", () => {
    (useScheduleData as Mock).mockReturnValue({
      hasData: true,
      isLoading: false,
      calendarRows: [
        { days: [{ exams: [] }] },
      ],
    });

    render(<CompactView />);
    // No course cards
    expect(screen.queryByTestId("course")).toBeNull();
  });
});
