import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, Mock } from "vitest";
import "@testing-library/jest-dom";

import DensityView from "./DensityView";


vi.mock("@/lib/hooks/useScheduleData", () => ({
  useScheduleData: vi.fn(),
}));

vi.mock("@/lib/store/calendarStore", () => {
  return {
    useCalendarStore: (fn: any) =>
      fn({
        colorTheme: "gray",
        setColorTheme: vi.fn(),
        selectCell: vi.fn(),
      }),
  };
});

vi.mock("@/lib/constants/colorThemes", () => ({
  colorThemes: {
    gray: ["#eee", "#ddd", "#ccc", "#bbb", "#aaa"],
  },
  THEME_KEYS: ["gray", "blue"],
}));

vi.mock("@/lib/utils", () => ({
  getReadableTextColorFromBg: () => "black",
}));

vi.mock("../CalendarGrid", () => ({
  CalendarGrid: ({ renderCell, data, days }: any) => (
    <div data-testid="calendar-grid">
      {data.map((row: any) =>
        row.days.map((cell: any, i: number) => (
          <div key={i} data-testid="grid-cell">
            {renderCell(cell)}
          </div>
        ))
      )}
    </div>
  ),
}));

vi.mock("@/components/common/EmptyScheduleState", () => ({
  EmptyScheduleState: ({ isLoading }: any) => (
    <div>{isLoading ? "Loading…" : "No Data"}</div>
  ),
}));

const { useScheduleData } = await import("@/lib/hooks/useScheduleData");
const { useCalendarStore } = await import("@/lib/store/calendarStore");

describe("DensityView Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders empty state when no data", () => {
    (useScheduleData as Mock).mockReturnValue({
      hasData: false,
      isLoading: false,
      calendarRows: [],
    });

    render(<DensityView />);

    expect(screen.getByText("No Data")).toBeInTheDocument();
  });

  it("renders loading state", () => {
    (useScheduleData as Mock).mockReturnValue({
      hasData: false,
      isLoading: true,
      calendarRows: [],
    });

    render(<DensityView />);

    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });

  it("renders density view header and theme select", () => {
    (useScheduleData as Mock).mockReturnValue({
      hasData: true,
      isLoading: false,
      calendarRows: [
        {
          days: [
            { examCount: 0, conflicts: 0 },
            { examCount: 2, conflicts: 1 },
          ],
        },
      ],
    });

    render(<DensityView />);

    expect(screen.getByText("Density View")).toBeInTheDocument();
    expect(
      screen.getByText("Color-coded heat map of exam distribution and conflicts")
    ).toBeInTheDocument();

    expect(screen.getByText("Theme: Gray")).toBeInTheDocument();
  });

  it("renders grid with correct exam count labels", () => {
    (useScheduleData as Mock).mockReturnValue({
      hasData: true,
      isLoading: false,
      calendarRows: [
        {
          days: [
            { examCount: 0, conflicts: 0 },
            { examCount: 2, conflicts: 1 },
          ],
        },
      ],
    });

    render(<DensityView />);

    expect(screen.getByText("No Exams")).toBeInTheDocument();
    expect(screen.getByText("2 Exams")).toBeInTheDocument();
    expect(screen.getByText("1 conflict")).toBeInTheDocument();
  });

  it("applies background colors based on thresholds", () => {
    (useScheduleData as Mock).mockReturnValue({
      hasData: true,
      isLoading: false,
      calendarRows: [
        {
          days: [
            { examCount: 0, conflicts: 0 }, 
            { examCount: 3, conflicts: 1 }, 
          ],
        },
      ],
    });

    render(<DensityView />);

    const cells = screen.getAllByTestId("grid-cell");

    expect(cells[0].firstChild).toHaveStyle("background-color: #eee");
  });

  it("calls selectCell when clicking non-zero exam cell", () => {
    const mockSelect = vi.fn();

    vi.mocked(useCalendarStore).mockImplementation((fn: any) =>
      fn({
        colorTheme: "gray",
        setColorTheme: vi.fn(),
        selectCell: mockSelect,
      })
    );

    (useScheduleData as Mock).mockReturnValue({
      hasData: true,
      isLoading: false,
      calendarRows: [
        { days: [{ examCount: 1, conflicts: 0 }] },
      ],
    });

    render(<DensityView />);

    const cell = screen.getByText("1 Exam");

    fireEvent.click(cell);

    expect(mockSelect).toHaveBeenCalledTimes(1);
  });

  it("does NOT call selectCell when clicking empty exam cell", () => {
    const mockSelect = vi.fn();

    vi.mocked(useCalendarStore).mockImplementation((fn: any) =>
      fn({
        colorTheme: "gray",
        setColorTheme: vi.fn(),
        selectCell: mockSelect,
      })
    );

    (useScheduleData as Mock).mockReturnValue({
      hasData: true,
      isLoading: false,
      calendarRows: [
        { days: [{ examCount: 0, conflicts: 0 }] },
      ],
    });

    render(<DensityView />);

    fireEvent.click(screen.getByText("No Exams"));

    expect(mockSelect).not.toHaveBeenCalled();
  });
});
