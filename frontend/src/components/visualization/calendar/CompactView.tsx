import { Ban } from "lucide-react";
import { useMemo } from "react";
import { EmptyScheduleState } from "@/components/common/EmptyScheduleState";
import { Button } from "@/components/ui/button";
import { useCourseMerges } from "@/lib/hooks/useCourseMerges";
import { useScheduleData } from "@/lib/hooks/useScheduleData";
import { useCalendarStore } from "@/lib/store/calendarStore";
import { extractTimeFromBlock } from "@/lib/utils";
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
  const { hasData, isLoading, calendarRows, schedule } = useScheduleData();
  const selectCell = useCalendarStore((state) => state.selectCell);
  const { isMerged } = useCourseMerges(schedule?.dataset_id);

  const blockoutMap = useMemo(() => {
    const map = new Map<string, number>();
    const blockouts = schedule?.blockouts;
    if (!blockouts) return map;
    for (const [day, slots] of Object.entries(blockouts)) {
      for (const [blockTime, count] of Object.entries(slots)) {
        map.set(`${day}-${blockTime}`, count);
      }
    }
    return map;
  }, [schedule]);

  if (!hasData) return <EmptyScheduleState isLoading={isLoading} />;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <div className="pl-2">
          <h1 className="text-2xl font-bold">Compact View</h1>
          <p className="text-muted-foreground">
            Detailed view of scheduled exams with course information
          </p>
        </div>
      </div>
      <CalendarGrid
        data={calendarRows}
        days={DAYS}
        minCellHeight="min-h-[120px]"
        renderCell={(cell) => {
          const maxVisible = 6;
          const visibleExams = cell.exams.slice(0, maxVisible);
          const hasMore = cell.exams.length > maxVisible;
          const blockedCount =
            blockoutMap.get(
              `${cell.day}-${extractTimeFromBlock(cell.timeSlot)}`,
            ) ?? 0;

          return (
            <div className="p-2 space-y-1 max-h-[150px] overflow-auto no-scrollbar">
              {visibleExams.map((exam) => (
                <Course
                  key={exam.id}
                  title={exam.courseCode}
                  students={exam.studentCount.toString()}
                  building={exam.building}
                  hasConflict={exam.conflicts > 0}
                  isMerged={isMerged(exam.section)}
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

              {blockedCount > 0 && (
                <div className="pt-1">
                  <span
                    className="inline-flex items-center gap-1 bg-orange-100 text-orange-700 text-[10px] font-medium rounded px-1.5 py-0.5"
                    title={`${blockedCount} room${blockedCount > 1 ? "s" : ""} blocked at this slot`}
                  >
                    <Ban className="h-2.5 w-2.5" />
                    {blockedCount} room{blockedCount > 1 ? "s" : ""} blocked
                  </span>
                </div>
              )}
            </div>
          );
        }}
      />
    </div>
  );
}
