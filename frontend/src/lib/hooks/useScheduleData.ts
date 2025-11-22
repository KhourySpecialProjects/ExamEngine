import { useMemo } from "react";
import type { CalendarRow, Exam } from "@/lib/types/calendar.types";
import { useSchedulesStore } from "@/lib/store/schedulesStore";
import type { CalendarExam } from "../api/schedules";

/**
 * Hook that transforms schedule data for different views
 * Single source of data transformation
 */
export function useScheduleData() {
  const currentSchedule = useSchedulesStore((state) => state.currentSchedule);
  const isGenerating = useSchedulesStore((state) => state.isGenerating);

  // Convert schedule to calendar rows
  const calendarRows = useMemo(() => {
    if (!currentSchedule) return [];
    return convertToCalendarRows(
      currentSchedule.schedule.calendar,
      currentSchedule.conflicts.breakdown,
    );
  }, [currentSchedule]);

  // Flatten to exam list
  const allExams = useMemo(() => {
    return calendarRows.flatMap((row) => row.days.flatMap((day) => day.exams));
  }, [calendarRows]);

  // Get departments
  const departments = useMemo(() => {
    return [...new Set(allExams.map((e) => e.department))].sort();
  }, [allExams]);

  // Get stats
  const stats = useMemo(
    () => ({
      totalExams: allExams.length,
      totalConflicts: allExams.reduce((sum, exam) => sum + exam.conflicts, 0),
    }),
    [allExams],
  );

  return {
    // Transformed data
    calendarRows,
    allExams,
    departments,
    stats,

    // State
    hasData: calendarRows.length > 0,
    isLoading: isGenerating,
    schedule: currentSchedule,
  };
}

/**
 * Convert backend calendar format to frontend CalendarRow format
 * Pure function - no side effects
 * TODO: Need better way of do data mapping
 */
function convertToCalendarRows(
  calendar: Record<string, Record<string, CalendarExam[]>>,
  conflictBreakdown: any[] = [],
): CalendarRow[] {
  const backendDays = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
  ];
  const frontendDays = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
  ];

  // Create a day name mapping (backend -> frontend)
  const dayNameMap: Record<string, string> = {
    Mon: "Monday",
    Tue: "Tuesday",
    Wed: "Wednesday",
    Thu: "Thursday",
    Fri: "Friday",
    Sat: "Saturday",
    Sun: "Sunday",
  };

  // Helper function to extract time from Block format "0 (9:00-11:00)" -> "9:00-11:00"
  const extractTimeFromBlock = (blockStr: string): string => {
    // If it's already just a time (like "9:00-11:00"), return it
    if (!blockStr.includes("(")) {
      return blockStr;
    }
    // Extract the part in parentheses: "0 (9:00-11:00)" -> "9:00-11:00"
    const match = blockStr.match(/\(([^)]+)\)/);
    return match ? match[1] : blockStr;
  };

  // Create a map of conflicts by day and time slot for quick lookup
  const conflictMap = new Map<string, number>();
  conflictBreakdown
    .filter((c) => c.conflict_type !== "back_to_back")
    .forEach((conflict) => {
      const day = conflict.day || "";
      const blockTime = conflict.block_time || "";
      if (day && blockTime) {
        // Map backend day names to frontend day names
        const frontendDay = dayNameMap[day] || day;
        // Normalize blockTime (extract time if it's in "N (time)" format)
        const normalizedTime = extractTimeFromBlock(blockTime);
        const key = `${frontendDay}-${normalizedTime}`;
        conflictMap.set(key, (conflictMap.get(key) || 0) + 1);
      }
    });

  // Get all time slots
  const timeSlotSet = new Set<string>();
  for (const daySchedule of Object.values(calendar)) {
    for (const timeSlot of Object.keys(daySchedule)) {
      timeSlotSet.add(timeSlot);
    }
  }

  // Helper function to extract start time for sorting
  const getStartTime = (timeSlot: string): number => {
    const match = timeSlot.match(/^(\d+):?(\d*)([AP]M)/);
    if (!match) return 0;

    let hours = parseInt(match[1], 10);
    const minutes = match[2] ? parseInt(match[2], 10) : 0;
    const period = match[3];

    if (period === "PM" && hours !== 12) hours += 12;
    if (period === "AM" && hours === 12) hours = 0;

    return hours * 60 + minutes;
  };

  // Sort time slots
  const timeSlots = Array.from(timeSlotSet).sort((a, b) => {
    return getStartTime(a) - getStartTime(b);
  });

  // Build rows
  return timeSlots.map((timeSlot) => ({
    timeSlot,
    days: frontendDays.map((frontendDay, index) => {
      const backendDay = backendDays[index];
      const examsInSlot = calendar[backendDay]?.[timeSlot] || [];

      // Use deterministic IDs instead of Math.random() to avoid hydration mismatch
      const exams: Exam[] = examsInSlot.map((exam, examIndex) => ({
        id: `${frontendDay}-${timeSlot}-${exam.CRN}-${examIndex}`,
        courseCode: exam.Course,
        section: exam.CRN,
        department: exam.Course.split(" ")[0] || "MISC",
        instructor: exam.Instructor || "TBD",
        studentCount: exam.Size,
        room: exam.Room,
        building: exam.Room.split(" ")[0] || "TBD",
        conflicts: exam.Valid ? 0 : 1,
        day: frontendDay,
        timeSlot,
      }));

      // Count conflicts for this cell from both exam validity and actual conflict breakdown
      // Extract time from timeSlot format "0 (9:00-11:00)" -> "9:00-11:00" to match conflict map
      const normalizedTimeSlot = extractTimeFromBlock(timeSlot);
      const cellConflictKey = `${frontendDay}-${normalizedTimeSlot}`;
      const actualConflicts = conflictMap.get(cellConflictKey) || 0;
      const invalidExams = exams.filter((e) => e.conflicts > 0).length;

      return {
        day: frontendDay,
        timeSlot,
        examCount: exams.length,
        conflicts: actualConflicts + invalidExams, // Combine both types
        exams,
      };
    }),
  }));
}
