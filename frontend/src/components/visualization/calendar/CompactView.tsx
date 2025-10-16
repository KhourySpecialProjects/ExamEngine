import { Button } from "@/components/ui/button";
import { CalendarGrid } from "./CalendarGrid";
import { useCalendarStore } from "@/lib/store/calendarStore";
const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];

/**
 * CompactView - Shows exam cards in calendar grid
 *
 * Displays up to 6 exams per cell with course code and student count.
 * Shows "+X more" button when there are additional exams.
 */
export default function CompactView() {
  const scheduleData = useCalendarStore((state) => state.scheduleData);
  const selectCell = useCalendarStore((state) => state.selectCell);
  return (
    <CalendarGrid
      data={scheduleData}
      days={DAYS}
      minCellHeight="min-h-[150px]"
      renderCell={(cell) => {
        const maxVisible = 6;
        const visibleExams = cell.exams.slice(0, maxVisible);
        const hasMore = cell.exams.length > maxVisible;

        if (cell.examCount === 0) {
          return <div className="p-2" />;
        }

        return (
          <div className="p-2 space-y-1 max-h-[150px] overflow-y-auto">
            {visibleExams.map((exam) => (
              <div
                key={exam.id}
                onClick={() => selectCell(cell)}
                className="bg-blue-50 border border-blue-200 rounded px-2 py-1 text-xs cursor-pointer hover:bg-blue-100 transition-colors"
              >
                <div className="font-medium text-blue-900">
                  {exam.courseCode}
                </div>
                <div className="text-gray-600">
                  {exam.studentCount} students
                </div>
              </div>
            ))}

            {hasMore && (
              <Button
                onClick={() => selectCell(cell)}
                className="text-xs text-blue-600 hover:text-blue-800 w-full text-left pl-2 py-1 bg-transparent hover:bg-transparent"
              >
                +{cell.exams.length - maxVisible} more
              </Button>
            )}
          </div>
        );
      }}
    />
  );
}
