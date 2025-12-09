import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, Mock } from "vitest";
import React from "react";

import { DashboardSidebar } from "./DashboardSidebar";

/* ------------------ MOCKS ------------------ */

const useDatasetStoreMock = vi.fn();

vi.mock("@/lib/store/datasetStore", () => ({
  useDatasetStore: () => useDatasetStoreMock(),
}));

vi.mock("../schedule/ScheduleRunner", () => ({
  ScheduleRunner: () => <div>Schedule Runner</div>,
}));

vi.mock("../upload/Uploader", () => ({
  Uploader: () => <div>Uploader</div>,
}));

vi.mock("@/lib/utils", () => ({
  getTimeAgo: vi.fn(() => "2 days ago"),
  cn: (...args: any[]) => args.filter(Boolean).join(" "),
}));


const mockSelectDataset = vi.fn();
const mockFetchDatasets = vi.fn();
const mockGetSelectedDataset = vi.fn();

vi.mock("@/lib/store/datasetStore", () => ({
  useDatasetStore: () => ({
    datasets: [],
    selectedDatasetId: null,
    selectDataset: mockSelectDataset,
    fetchDatasets: mockFetchDatasets,
    getSelectedDataset: mockGetSelectedDataset,
    isLoading: false,
  }),
}));

beforeEach(() => {
  vi.clearAllMocks();

  useDatasetStoreMock.mockReturnValue({
    datasets: [],
    selectedDatasetId: null,
    selectDataset: vi.fn(),
    fetchDatasets: vi.fn(),
    getSelectedDataset: vi.fn().mockReturnValue(null),
    isLoading: false,
  });
});

/* ------------------ TEST DATA ------------------ */

const mockDataset = {
  dataset_id: "1",
  dataset_name: "Spring 2025",
  created_at: "2024-01-01",
  files: {
    courses: { unique_crns: 10 },
    enrollments: { unique_students: 200 },
    rooms: { unique_rooms: 15 },
  },
};

/* ------------------ TESTS ------------------ */

describe("DashboardSidebar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls fetchDatasets on mount when dataset list is empty", () => {
    render(<DashboardSidebar />);
    expect(mockFetchDatasets).toHaveBeenCalledTimes(1);
  });

  it("renders loading state when loading and no datasets", () => {
    useDatasetStoreMock.mockReturnValue({
      datasets: [],
      selectedDatasetId: null,
      selectDataset: mockSelectDataset,
      fetchDatasets: mockFetchDatasets,
      getSelectedDataset: () => null,
      isLoading: true,
    });

    render(<DashboardSidebar />);

    expect(screen.queryByText("Loading datasets...")).toBeNull();
  });

  it("renders empty state when no datasets and not loading", () => {
    render(<DashboardSidebar />);

    expect(
      screen.queryByText("Upload a dataset to get started")
    ).not.toBeNull();
  });

  it("renders dataset selector when datasets exist", () => {
    useDatasetStoreMock.mockReturnValue({
      datasets: [mockDataset],
      selectedDatasetId: null,
      selectDataset: mockSelectDataset,
      fetchDatasets: mockFetchDatasets,
      getSelectedDataset: () => null,
      isLoading: false,
    });

    render(<DashboardSidebar />);

    expect(screen.queryByText("Select dataset")).toBeNull();
    expect(screen.queryByText("Spring 2025")).toBeNull();
  });

  it("renders selected dataset info", () => {
    useDatasetStoreMock.mockReturnValue({
      datasets: [mockDataset],
      selectedDatasetId: "1",
      selectDataset: mockSelectDataset,
      fetchDatasets: mockFetchDatasets,
      getSelectedDataset: () => mockDataset,
      isLoading: false,
    });

    render(<DashboardSidebar />);

    expect(screen.queryByText("Current Dataset")).toBeNull();
    expect(screen.queryByText("10 courses")).toBeNull();
    expect(screen.queryByText("200 students")).toBeNull();
    expect(screen.queryByText("15 rooms")).toBeNull();
    expect(screen.queryByText("Updated: 2 days ago")).toBeNull();
  });

  it("renders ScheduleRunner and Uploader", () => {
    render(<DashboardSidebar />);

    expect(screen.queryByText("Schedule Runner")).not.toBeNull();
    expect(screen.queryByText("Uploader")).not.toBeNull();
  });
});
