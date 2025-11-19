import type { DatasetMetadata } from "../api/datasets";

export interface DatasetState {
  // State
  datasets: DatasetMetadata[];
  selectedDatasetId: string | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  fetchDatasets: () => Promise<void>;
  selectDataset: (datasetId: string | null) => void;
  deleteDataset: (datasetId: string) => Promise<void>;
  clearError: () => void;
  refreshDatasets: () => Promise<void>;

  // Computed
  getSelectedDataset: () => DatasetMetadata | null;
  getDatasetById: (datasetId: string) => DatasetMetadata | null;
}

