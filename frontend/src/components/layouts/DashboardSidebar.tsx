"use client";

import {
  Building,
  Calendar,
  Database,
  SlidersHorizontal,
  Users,
} from "lucide-react";
import { useEffect } from "react";
import { useDatasetStore } from "@/lib/store/datasetStore";
import { getTimeAgo } from "@/lib/utils";
import { DatasetBar } from "../dataset/DatasetBar";
import { ScheduleRunner } from "../schedule/ScheduleRunner";
import { Uploader } from "../upload/Uploader";
export function DashboardSidebar() {
  const { datasets, fetchDatasets, getSelectedDataset } = useDatasetStore();

  const selectedDataset = getSelectedDataset();
  useEffect(() => {
    // Fetch datasets on mount
    if (datasets.length === 0) {
      fetchDatasets();
    }
  }, [fetchDatasets, datasets.length]);

  return (
    <div className="p-6 space-y-6">
      <section>
        <div className="flex items-center gap-2 mb-3">
          <Database className="text-green-800" />
          <h2 className="font-semibold text-sm">Data Management</h2>
        </div>

        {/*Select & Delete Components*/}

        <DatasetBar />
        {/* Upload Button */}
        <Uploader />

        {/* Dataset Info */}
        {selectedDataset ? (
          <div className="mt-3 text-sm space-y-2">
            <div className="font-medium text-foreground">Current Dataset</div>

            <div className="space-y-1 text-muted-foreground">
              <div className="flex items-center gap-2">
                <Database className="h-3.5 w-3.5" />
                <span>{selectedDataset.files.courses.unique_crns} courses</span>
              </div>

              <div className="flex items-center gap-2">
                <Users className="h-3.5 w-3.5" />
                <span>
                  {selectedDataset.files.enrollments.unique_students} students
                </span>
              </div>

              <div className="flex items-center gap-2">
                <Building className="h-3.5 w-3.5" />
                <span>{selectedDataset.files.rooms.unique_rooms} rooms</span>
              </div>

              <div className="flex items-center gap-2">
                <Calendar className="h-3.5 w-3.5" />
                <span>Updated: {getTimeAgo(selectedDataset.created_at)}</span>
              </div>
            </div>
          </div>
        ) : (
          <div className="mt-3 text-sm text-muted-foreground text-center py-4">
            {datasets.length === 0 ? (
              <span>Upload a dataset to get started</span>
            ) : (
              <span>Select a dataset above</span>
            )}
          </div>
        )}
      </section>

      <section>
        <div className="flex items-center gap-2 mb-3">
          <SlidersHorizontal />
          <h2 className="font-semibold text-sm">Optimization Controls</h2>
        </div>
        <ScheduleRunner />
      </section>
    </div>
  );
}
