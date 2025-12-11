import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { ScheduleRunner } from "./ScheduleRunner";


vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
    loading: vi.fn(() => "toast-id"),
  },
}));

const mockUseDatasetStore = vi.fn();

vi.mock("@/lib/store/datasetStore", () => ({
  useDatasetStore: (selector: any) => selector(mockUseDatasetStore()),
}));

const mockUseScheduleStore = vi.fn();

vi.mock("@/lib/store/scheduleStore", () => ({
  useScheduleStore: () => mockUseScheduleStore(),
}));

vi.mock("@/components/ui/dialog", () => ({
  Dialog: ({ children }: any) => <div>{children}</div>,
  DialogTrigger: ({ children }: any) => <div>{children}</div>,
  DialogContent: ({ children }: any) => <div>{children}</div>,
  DialogHeader: ({ children }: any) => <div>{children}</div>,
  DialogTitle: ({ children }: any) => <div>{children}</div>,
  DialogDescription: ({ children }: any) => <div>{children}</div>,
}));

vi.mock("@/components/ui/button", () => ({
  Button: ({ children, onClick, disabled }: any) => (
    <button disabled={disabled} onClick={onClick}>
      {children}
    </button>
  ),
}));

vi.mock("@/components/ui/input", () => ({
  Input: ({ value, onChange }: any) => (
    <input value={value} onChange={onChange} />
  ),
}));

vi.mock("@/components/ui/slider", () => ({
  Slider: ({ onValueChange }: any) => (
    <div data-testid="slider" onClick={() => onValueChange([4])} />
  ),
}));

vi.mock("@/components/ui/switch", () => ({
  Switch: ({ checked, onCheckedChange }: any) => (
    <button onClick={() => onCheckedChange(!checked)}>toggle</button>
  ),
}));

vi.mock("@/components/ui/alert", () => ({
  Alert: ({ children }: any) => <div>{children}</div>,
  AlertDescription: ({ children }: any) => <div>{children}</div>,
}));

vi.mock("@/components/ui/label", () => ({
  Label: ({ children }: any) => <label>{children}</label>,
}));

vi.mock("@/components/ui/separator", () => ({
  Separator: () => <div />,
}));

const baseDatasetState = {
  selectedDatasetId: "ds1",
  getSelectedDataset: () => ({
    dataset_name: "Test Dataset",
    files: {
      courses: { unique_crns: 10 },
      enrollments: { unique_students: 100 },
      rooms: { unique_rooms: 5 },
    },
  }),
};

const baseScheduleState = {
  currentSchedule: null,
  isGenerating: false,
  scheduleName: "Finals",
  parameters: {
    student_max_per_day: 3,
    instructor_max_per_day: 2,
    max_days: 7,
    avoid_back_to_back: true,
  },
  generateSchedule: vi.fn(),
  setParameters: vi.fn(),
  setScheduleName: vi.fn(),
};

beforeEach(() => {
  vi.clearAllMocks();
  mockUseDatasetStore.mockReturnValue(baseDatasetState);
  mockUseScheduleStore.mockReturnValue(baseScheduleState);
});

describe("ScheduleRunner", () => {
  it("renders Optimize button", () => {
    render(<ScheduleRunner />);
    expect(
    screen.getByText((content) =>
      content.includes("Optimize Exam Schedule")
    )
  ).toBeTruthy();
  });

  it("shows selected dataset info", () => {
    render(<ScheduleRunner />);
    expect(
    screen.getByText((content) =>
      content.includes("Test") && content.includes("Dataset")
    )
  ).toBeTruthy();

  expect(
    screen.getByText((content) =>
      content.includes("10") && content.includes("courses")
    )
  ).toBeTruthy();

  expect(
    screen.getByText((content) =>
      content.includes("100") && content.includes("students")
    )
  ).toBeTruthy();
  expect(
    screen.getByText((content) =>
      content.includes("5") && content.includes("rooms")
    )
  ).toBeTruthy();
  });


  it("successfully generates schedule", async () => {
    baseScheduleState.generateSchedule.mockResolvedValue({
      schedule: { total_exams: 12 },
    });

    render(<ScheduleRunner />);
    fireEvent.click(screen.getByText("Generate Schedule"));

    const { toast } = await import("sonner");

    await waitFor(() => {
      expect(baseScheduleState.generateSchedule).toHaveBeenCalledWith("ds1");
      expect(toast.success).toHaveBeenCalledWith(
        "Schedule generated!",
        expect.anything(),
      );
    });
  });

  it("handles generation failure", async () => {
    baseScheduleState.generateSchedule.mockRejectedValue(
      new Error("Boom"),
    );

    render(<ScheduleRunner />);
    fireEvent.click(screen.getByText("Generate Schedule"));

    const { toast } = await import("sonner");

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalled();
    });
  });

  it("shows current schedule info when available", () => {
    mockUseScheduleStore.mockReturnValue({
      ...baseScheduleState,
      currentSchedule: {
        schedule: { total_exams: 5 },
        summary: { real_conflicts: 2 },
        failures: [],
        conflicts: { total: 1 },
      },
    });

    render(<ScheduleRunner />);

    expect(
    screen.getByText((content) =>
      content.includes("5") && content.includes("exams")
    )
  ).toBeTruthy();

  expect(
    screen.getByText((content) =>
      content.includes("2") && content.includes("conflicts")
    )
  ).toBeTruthy();

  expect(
    screen.getByText((content) =>
      content.includes("1") && content.includes("back-to-back")
    )
  ).toBeTruthy();
  });

  it("shows loading state when generating", () => {
    mockUseScheduleStore.mockReturnValue({
      ...baseScheduleState,
      isGenerating: true,
    });

    render(<ScheduleRunner />);
    expect(screen.getByText("Generating...")).toBeTruthy();
  });
});
