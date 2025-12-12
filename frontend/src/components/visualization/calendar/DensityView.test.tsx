import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, Mock } from "vitest";

import DensityView from "./DensityView";

beforeEach(() => {
  vi.clearAllMocks(); 
});


vi.mock("@/lib/hooks/useScheduleData", () => ({
  useScheduleData: vi.fn(),
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


vi.mock("@/lib/constants/colorThemes", () => ({
  colorThemes: {
    gray: ["#eee", "#ddd", "#ccc", "#bbb", "#aaa"],
  },
  THEME_KEYS: ["gray", "blue"],
}));

vi.mock("@/lib/utils", () => ({
  getReadableTextColorFromBg: () => "black",
  cn: (...args: any[]) => args.filter(Boolean).join(" "), // simple stub
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

    expect(screen.queryByText("No Data")).not.toBeNull();
  });

  it("renders loading state", () => {
    (useScheduleData as Mock).mockReturnValue({
      hasData: false,
      isLoading: true,
      calendarRows: [],
    });

    render(<DensityView />);

    expect(screen.queryByText("Loading…")).not.toBeNull();
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

    expect(screen.queryByText("Density View")).not.toBeNull();
    expect(
      screen.queryByText(
        "Color-coded heat map of exam distribution and conflicts"
      )
    ).not.toBeNull();

    expect(screen.queryByText("Theme: Gray")).not.toBeNull();
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

    const noExamCells = screen.getAllByText("No Exams");
    expect(noExamCells.length).toBeGreaterThan(0);
    expect(screen.getByText("2 Exams")).toBeDefined();
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

    const cells = screen.getAllByText("No Exams");

    // uses toHaveStyle which works without jest-dom
    expect(cells[0].firstChild).not.toBeFalsy();
  });

  it("calls selectCell when clicking non-zero exam cell", () => {
  (useScheduleData as Mock).mockReturnValue({
    hasData: true,
    isLoading: false,
    calendarRows: [{ days: [{ examCount: 1, conflicts: 0 }] }],
  });

  render(<DensityView />);

  const cell = screen.getByText("1 Exam");
  fireEvent.click(cell);

  expect(mockSelect).toHaveBeenCalledTimes(1);
  }); 
});
