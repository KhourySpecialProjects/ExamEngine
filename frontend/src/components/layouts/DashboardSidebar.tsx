"use client";

import {
  Building,
  Calendar,
  Database,
  Menu,
  PanelLeftClose,
  Shield,
  SlidersHorizontal,
  Users,
} from "lucide-react";
import { useEffect } from "react";
import { useAuthStore } from "@/lib/store/authStore";
import { useDatasetStore } from "@/lib/store/datasetStore";
import { getTimeAgo } from "@/lib/utils";
import { DatasetBar } from "../dataset/DatasetBar";
import { ScheduleRunner } from "../schedule/ScheduleRunner";
import { Button } from "../ui/button";
import { Uploader } from "../upload/Uploader";

type SidebarProps = {
  isOpen?: boolean;
  onToggle?: () => void;
};

export function DashboardSidebar({ isOpen = true, onToggle }: SidebarProps) {
  const {
    datasets,
    selectedDatasetId,
    selectDataset,
    fetchDatasets,
    getSelectedDataset,
    isLoading,
  } = useDatasetStore();
  const { user } = useAuthStore();

  const selectedDataset = getSelectedDataset();
  useEffect(() => {
    // Fetch datasets on mount
    if (datasets.length === 0) {
      fetchDatasets();
    }
  }, [fetchDatasets, datasets.length]);

  return (
    <div className="h-full flex flex-col">
      <div
        className={`flex items-center border-b py-3 ${
          isOpen ? "justify-between px-3" : "justify-center px-1"
        }`}
      >
        <div className={`${isOpen ? "flex items-center gap-2" : "hidden"}`}>
          <Database className="text-green-800" />
          <h2 className="font-semibold text-sm">Data Management</h2>
        </div>
        {onToggle && (
          <Button
            variant="ghost"
            size="icon"
            onClick={onToggle}
            aria-label={isOpen ? "Collapse sidebar" : "Expand sidebar"}
            className="h-9 w-9"
          >
            {isOpen ? (
              <PanelLeftClose className="h-5 w-5" />
            ) : (
              <Menu className="h-5 w-5" />
            )}
          </Button>
        )}
      </div>

      <div
        className={`flex-1 overflow-y-auto transition-all duration-150 ${
          isOpen
            ? "opacity-100 p-6 pointer-events-auto"
            : "opacity-0 p-0 pointer-events-none"
        }`}
      >
        <div className="space-y-6">
          <section>
            {/*Select & Delete Components*/}
            <DatasetBar />
            {/* Upload Button */}
            <Uploader />

            {/* Dataset Info */}
            {selectedDataset ? (
              <div className="mt-3 text-sm space-y-2">
                <div className="font-medium text-foreground">
                  Current Dataset
                </div>

                <div className="space-y-1 text-muted-foreground">
                  <div className="flex items-center gap-2">
                    <Database className="h-3.5 w-3.5" />
                    <span>
                      {selectedDataset.files.courses.unique_crns} courses
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <Users className="h-3.5 w-3.5" />
                    <span>
                      {selectedDataset.files.enrollments.unique_students}{" "}
                      students
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <Building className="h-3.5 w-3.5" />
                    <span>
                      {selectedDataset.files.rooms.unique_rooms} rooms
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <Calendar className="h-3.5 w-3.5" />
                    <span>
                      Updated: {getTimeAgo(selectedDataset.created_at)}
                    </span>
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
      </div>
    </div>
  );
}
