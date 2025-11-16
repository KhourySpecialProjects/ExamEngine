import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, Mock } from "vitest";
import CompactView from "./CompactView";

// ─── Mocks ───────────────────────────────────────────────

vi.mock("@/lib/hooks/useScheduleData", () => ({
  useScheduleData: vi.fn(),
}));

vi.mock("@/components/common/EmptyScheduleState", () => ({
  EmptyScheduleState: ({ isLoading }: any) => (
    <div>{isLoading ? "Loading…" : "No Data"}</div>
  ),
}));

// Mock Zustand calendar store
vi.mock("@/lib/store/calendarStore", () => ({
  useCalendarStore: (fn: any) =>
    fn({
      selectCell: vi.fn(),
    }),
}));

// Mock Course component
vi.mock("../Course", () => ({
  Course: ({ title, students }: any) => (
    <div data-testid="course">
      {title} - {students} students
    </div>
  ),
}));

// Mock CalendarGrid to emit cells with renderCell
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

  // ───────────────────────────────────────────────

  it("renders empty state when no data", () => {
    (useScheduleData as Mock).mockReturnValue({
      hasData: false,
      isLoading: false,
      calendarRows: [],
    });

    render(<CompactView />);
    expect(screen.getByText("No Data")).toBeInTheDocument();
  });

  // ───────────────────────────────────────────────

  it("renders title and subtitle when data available", () => {
    (useScheduleData as Mock).mockReturnValue({
      hasData: true,
      isLoading: false,
      calendarRows: [
        { days: [{ exams: [] }] },
      ],
    });

    render(<CompactView />);

    expect(screen.getByText("Compact View")).toBeInTheDocument();
    expect(
      screen.getByText("Detailed view of scheduled exams with course information")
    ).toBeInTheDocument();
  });

  // ───────────────────────────────────────────────

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

  // ───────────────────────────────────────────────

  it('shows "+X more" when cell has extra exams', () => {
    const exams = Array.from({ length: 9 }).map((_, i) => ({
      id: i,
      courseCode: `CSE${i}`,
      studentCount: 10,
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

    expect(screen.getByText("+3 more")).toBeInTheDocument();
  });

  // ───────────────────────────────────────────────

  it("calls selectCell when clicking '+X more' button", () => {
    const mockSelect = vi.fn();

    // Override store mock
    vi.mocked(useCalendarStore).mockImplementation((fn: any) =>
      fn({ selectCell: mockSelect })
    );

    const exams = Array.from({ length: 7 }).map((_, i) => ({
      id: i,
      courseCode: `CSE${i}`,
      studentCount: 10,
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

    const moreBtn = screen.getByText("+1 more");
    fireEvent.click(moreBtn);

    expect(mockSelect).toHaveBeenCalledTimes(1);
  });

  // ───────────────────────────────────────────────

  it("handles empty exam cells correctly", () => {
    (useScheduleData as Mock).mockReturnValue({
      hasData: true,
      isLoading: false,
      calendarRows: [
        { days: [{ exams: [] }] },
      ],
    });

    render(<CompactView />);

    // Should render nothing, but grid cell exists
    expect(screen.getByTestId("grid-cell")).toBeInTheDocument();

    // No course cards
    expect(screen.queryByTestId("course")).toBeNull();
  });
});
