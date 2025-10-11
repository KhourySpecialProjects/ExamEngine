"use client";

import { AlertCircle } from "lucide-react";
import { useCalendarStore } from "@/store/calendarStore";
import { CalendarGrid } from "./CalendarGrid";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
/**
 * Get color based on exam density
 */
const getDensityColor = (count: number): string => {
  if (count === 0) return "bg-gray-50 text-gray-400 border-gray-200";
  if (count <= 10) return "bg-green-100 text-green-900 border-green-300";
  if (count <= 20) return "bg-yellow-100 text-yellow-900 border-yellow-300";
  if (count <= 60) return "bg-orange-200 text-orange-900 border-orange-400";
  return "bg-red-300 text-red-900 border-red-500";
};
/**
 * DensityMapView - Heatmap visualization of exam schedule
 *
 * Shows exam count with color-coded density.
 * Click cell to open detail modal.
 */
export default function DensityView() {
  const scheduleData = useCalendarStore((state) => state.scheduleData);
  const selectCell = useCalendarStore((state) => state.selectCell);

  return (
    <div className="space-y-4">
      {/* Calendar Grid */}
      <CalendarGrid
        data={scheduleData}
        days={DAYS}
        renderCell={(cell) => {
          const colorClass = getDensityColor(cell.examCount);

          return (
            <div
              onClick={() => cell.examCount > 0 && selectCell(cell)}
              className={`
                ${colorClass} border-2 rounded-lg
                min-h-[120px] m-3 cursor-pointer 
                transition-all duration-200
                ${cell.examCount > 0 ? "hover:scale-105 hover:shadow-lg hover:z-10 relative" : ""}
              `}
            >
              <div className="flex flex-col items-center justify-center h-full pt-3">
                {/* Exam Count */}
                <div className="text-4xl font-bold mb-1">{cell.examCount}</div>

                {/* Label */}
                <div className="text-xs font-medium mb-2">
                  {cell.examCount === 1 ? "exam" : "exams"}
                </div>

                {/* Conflict Indicator */}
                {cell.conflicts > 0 && (
                  <div className="flex items-center gap-1 text-xs bg-red-500 text-white px-2 py-0.5 rounded-full">
                    <AlertCircle className="size-3" />
                    {cell.conflicts}
                  </div>
                )}
              </div>
            </div>
          );
        }}
      />

      {/* Legend */}
      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="font-semibold mb-3 text-sm">Density Legend</h3>
        <div className="flex gap-3 items-center flex-wrap text-sm">
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 bg-gray-50 border-2 border-gray-200 rounded"></div>
            <span>Empty</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 bg-green-100 border-2 border-green-300 rounded"></div>
            <span>1-5</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 bg-yellow-100 border-2 border-yellow-300 rounded"></div>
            <span>6-10</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 bg-orange-200 border-2 border-orange-400 rounded"></div>
            <span>11-20</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 bg-red-300 border-2 border-red-500 rounded"></div>
            <span>20+</span>
          </div>
        </div>
      </div>
    </div>
  );
}
