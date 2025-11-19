import { create } from "zustand";
import { persist } from "zustand/middleware";
import { apiClient } from "../api/client";
import type { DatasetMetadata } from "../api/datasets";

interface DatasetState {
  // State
  datasets: DatasetMetadata[];
  selectedDatasetId: string | null;
  selectedDeleteDataset: DatasetMetadata | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  fetchDatasets: () => Promise<void>;
  selectDataset: (datasetId: string | null) => void;
  selectDeleteDataset: (dataset: DatasetMetadata | null) => void;
  deleteDataset: (datasetId: string) => Promise<void>;
  clearError: () => void;
  refreshDatasets: () => Promise<void>;

  // Computed
  getSelectedDataset: () => DatasetMetadata | null;
  getDatasetById: (datasetId: string) => DatasetMetadata | null;
}

export const useDatasetStore = create<DatasetState>()(
  persist(
    (set, get) => ({
      // Initial state
      datasets: [],
      selectedDatasetId: null,
      isLoading: false,
      selectedDeleteDataset: null,
      error: null,

      selectDeleteDataset: (dataset: DatasetMetadata | null) => {
        set({ selectedDeleteDataset: dataset });
      },

      // Fetch all datasets
      fetchDatasets: async () => {
        set({ isLoading: true, error: null });
        try {
          const datasets = await apiClient.datasets.list();
          set({ datasets, isLoading: false });
        } catch (error) {
          set({
            error:
              error instanceof Error
                ? error.message
                : "Failed to fetch datasets",
            isLoading: false,
          });
        }
      },

      // Select a dataset
      selectDataset: (datasetId: string | null) => {
        set({ selectedDatasetId: datasetId });
      },

      // Delete a dataset
      deleteDataset: async (datasetId: string) => {
        set({ isLoading: true, error: null });
        try {
          await apiClient.datasets.deleteDataset(datasetId);

          set((state) => ({
            datasets: state.datasets.filter((d) => d.dataset_id !== datasetId),
            selectedDatasetId:
              state.selectedDatasetId === datasetId
                ? null
                : state.selectedDatasetId,
            isLoading: false,
          }));
        } catch (error) {
          set({
            error:
              error instanceof Error
                ? error.message
                : "Failed to delete dataset",
            isLoading: false,
          });
          throw error;
        }
      },

      // Clear error
      clearError: () => {
        set({ error: null });
      },

      // Refresh datasets (alias for fetchDatasets)
      refreshDatasets: async () => {
        await get().fetchDatasets();
      },

      // Get selected dataset
      getSelectedDataset: () => {
        const state = get();
        if (!state.selectedDatasetId) return null;
        return (
          state.datasets.find(
            (d) => d.dataset_id === state.selectedDatasetId,
          ) || null
        );
      },

      // Get dataset by ID
      getDatasetById: (datasetId: string) => {
        const state = get();
        return state.datasets.find((d) => d.dataset_id === datasetId) || null;
      },
    }),
    {
      name: "dataset-storage", // localStorage key
      partialize: (state) => ({
        // Only persist these fields
        selectedDatasetId: state.selectedDatasetId,
      }),
    },
  ),
);
