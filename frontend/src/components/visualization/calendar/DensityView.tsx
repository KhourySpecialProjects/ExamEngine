import { useMemo } from "react";
import { EmptyScheduleState } from "@/components/common/EmptyScheduleState";
import { useScheduleData } from "@/lib/hooks/useScheduleData";
import { useCalendarStore } from "@/lib/store/calendarStore";
import { CalendarGrid } from "./CalendarGrid";

const DAYS = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];
/**
 * Calculate dynamic thresholds based on data distribution (percentile)
 */
const calculateThresholds = (counts: number[]) => {
  const nonZero = counts.filter((c) => c > 0).sort((a, b) => a - b);
  if (nonZero.length === 0) return { t1: 0, t2: 0, t3: 0, t4: 0 };

  const len = nonZero.length;
  return {
    t1: nonZero[Math.floor(len * 0.25)] || nonZero[0],
    t2: nonZero[Math.floor(len * 0.5)] || nonZero[0],
    t3: nonZero[Math.floor(len * 0.75)] || nonZero[0],
    t4: nonZero[len - 1],
  };
};

/**
 * Get color based on thresholds
 */
const getDensityColor = (
  count: number,
  thresholds: ReturnType<typeof calculateThresholds>,
): string => {
  if (count === 0) return "bg-gray-50 text-gray-400";
  if (count <= thresholds.t1) return "bg-gray-100 text-gray-900";
  if (count <= thresholds.t2) return "bg-gray-300 text-gray-900";
  if (count <= thresholds.t3) return "bg-gray-500 text-white";
  return "bg-gray-700 text-white";
};

/**
 * DensityMapView - Heatmap visualization of exam schedule
 *
 * Shows exam count with color-coded density.
 * Click cell to open detail modal.
 */
export default function DensityView() {
  const { hasData, isLoading, calendarRows } = useScheduleData();
  const selectCell = useCalendarStore((state) => state.selectCell);
  const thresholds = useMemo(() => {
    const counts = calendarRows.flatMap((row) =>
      row.days.map((d) => d.examCount),
    );
    return calculateThresholds(counts);
  }, [calendarRows]);

  if (!hasData) return <EmptyScheduleState isLoading={isLoading} />;

  return (
    <div className="space-y-4">
      {/* Calendar Grid */}
      <CalendarGrid
        data={calendarRows}
        days={DAYS}
        minCellHeight="h-[120px]"
        minCellWidth={140}
        defaultCellWidth={140}
        timeSlotWidth={140}
        renderCell={(cell) => {
          const colorClass = getDensityColor(
            cell ? cell.examCount : 0,
            thresholds,
          );
          const examCount = cell ? cell.examCount : 0;
          const conflicts = cell ? cell.conflicts : 0;

          return (
            <div
              onClick={() => examCount > 0 && cell && selectCell(cell)}
              className={`
                ${colorClass}
                w-full h-full
                flex items-center
                border border-gray-200
                ${examCount > 0 ? "cursor-pointer hover:shadow-lg hover:z-10 relative transition-all duration-200" : "cursor-default"}
              `}
            >
              <div className="flex flex-col items-start justify-start p-3 w-full h-full">
                {/* Exam Count */}
                <div className="text-base font-semibold leading-tight">
                  {examCount === 0
                    ? "No Exams"
                    : `${examCount} ${examCount === 1 ? "Exam" : "Exams"}`}
                </div>

                {/* Conflict Indicator */}
                <div className="text-xs font-normal pt-1">
                  {conflicts === 0
                    ? "No conflicts"
                    : `${conflicts} ${conflicts === 1 ? "conflict" : "conflicts"}`}
                </div>
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
            <div className="w-10 h-10 bg-white border-2 border-gray-300 rounded" />
            <span>0</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 bg-gray-50  border-2 border-gray-50 rounded" />
            <span>1-{thresholds.t1}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 bg-gray-100 border-2 border-gray-100 rounded" />
            <span>
              {thresholds.t1 + 1}-{thresholds.t2}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 bg-gray-300 border-2 border-gray-300 rounded" />
            <span>
              {thresholds.t2 + 1}-{thresholds.t3}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 bg-gray-700 border-2 border-gray-300 rounded" />
            <span className="text-white bg-gray-700 px-2 py-0.5 rounded">
              {thresholds.t3 + 1}+
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
