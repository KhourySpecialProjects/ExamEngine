import { EmptyScheduleState } from "@/components/common/EmptyScheduleState";
import { Button } from "@/components/ui/button";
import { useScheduleData } from "@/lib/hooks/useScheduleData";
import { useCalendarStore } from "@/lib/store/calendarStore";
import { Course } from "../Course";
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
 * CompactView - Shows exam cards in calendar grid
 *
 * Displays up to 6 exams per cell with course code and student count.
 * Shows "+X more" button when there are additional exams.
 */
export default function CompactView() {
  const { hasData, isLoading, calendarRows } = useScheduleData();
  const selectCell = useCalendarStore((state) => state.selectCell);
  if (!hasData) return <EmptyScheduleState isLoading={isLoading} />;

  return (
    <CalendarGrid
      data={calendarRows}
      days={DAYS}
      minCellHeight="min-h-[150px]"
      renderCell={(cell) => {
        const maxVisible = 6;
        const visibleExams = cell.exams.slice(0, maxVisible);
        const hasMore = cell.exams.length > maxVisible;
        return (
          <div className="p-2 space-y-1 max-h-[150px] overflow-auto no-scrollbar">
            {visibleExams.map((exam) => (
              <Course
                key={exam.id}
                title={exam.courseCode}
                students={exam.studentCount.toString()}
                building={exam.building}
              />
            ))}

            {hasMore && (
              <Button
                onClick={() => selectCell(cell)}
                className="text-xs text-blue-600 hover:text-blue-800 w-full text-left pl-2 py-1 bg-transparent hover:bg-transparent"
              >
                {"+"}
                {cell.exams.length - maxVisible} more
              </Button>
            )}
          </div>
        );
      }}
    />
  );
}
