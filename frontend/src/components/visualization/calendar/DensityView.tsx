import { useCalendarStore } from "@/lib/store/calendarStore";
import { CalendarGrid } from "./CalendarGrid";
import { useScheduleData } from "@/lib/hooks/useScheduleData";
import { EmptyScheduleState } from "@/components/common/EmptyScheduleState";

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
 * Get color based on exam density
 */
const getDensityColor = (count: number): string => {
  if (count === 0) return "bg-white text-black";
  if (count <= 30) return "bg-[#E3F5FF] text-black";
  if (count <= 60) return "bg-[#FFEA94] text-black";
  if (count <= 70) return "bg-[#FFD4D4] text-black";
  return "bg-red-400 text-black";
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
          const colorClass = getDensityColor(cell ? cell.examCount : 0);
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
            <span>No Exams</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 bg-[#E3F5FF] border-2 border-blue-200 rounded" />
            <span>1-30</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 bg-[#FFEA94] border-2 border-yellow-300 rounded" />
            <span>31-60</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 bg-[#FFD4D4] border-2 border-red-200 rounded" />
            <span>61-70</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 bg-[#D7000A] border-2 border-red-600 rounded" />
            <span className="text-white bg-[#D7000A] px-2 py-0.5 rounded">
              71+
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
