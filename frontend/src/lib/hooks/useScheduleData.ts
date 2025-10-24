import { useMemo } from "react";
import type { CalendarRow, Exam } from "@/lib/store/calendarStore";
import { useScheduleStore } from "@/lib/store/scheduleStore";
import type { CalendarExam } from "../api/schedules";

/**
 * Hook that transforms schedule data for different views
 * Single source of data transformation
 */
export function useScheduleData() {
  const currentSchedule = useScheduleStore((state) => state.currentSchedule);
  const isGenerating = useScheduleStore((state) => state.isGenerating);

  // Convert schedule to calendar rows
  const calendarRows = useMemo(() => {
    if (!currentSchedule) return [];
    return convertToCalendarRows(currentSchedule.schedule.calendar);
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
): CalendarRow[] {
  const backendDays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  const frontendDays = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
  ];

  // Get all time slots
  const timeSlotSet = new Set<string>();
  for (const daySchedule of Object.values(calendar)) {
    for (const timeSlot of Object.keys(daySchedule)) {
      timeSlotSet.add(timeSlot);
    }
  }

  const timeSlots = Array.from(timeSlotSet).sort();

  // Build rows
  return timeSlots.map((timeSlot) => ({
    timeSlot,
    days: frontendDays.map((frontendDay, index) => {
      const backendDay = backendDays[index];
      const examsInSlot = calendar[backendDay]?.[timeSlot] || [];

      const exams: Exam[] = examsInSlot.map((exam) => ({
        id: `${frontendDay}-${timeSlot}-${exam.CRN}-${Math.random() * 5000}`,
        courseCode: exam.Course,
        section: exam.CRN,
        department: exam.Course.split(" ")[0] || "MISC",
        instructor: "TBD",
        studentCount: exam.Size,
        room: exam.Room,
        building: exam.Room.split(" ")[0] || "TBD",
        conflicts: exam.Valid ? 0 : 1,
        day: frontendDay,
        timeSlot,
      }));

      return {
        day: frontendDay,
        timeSlot,
        examCount: exams.length,
        conflicts: exams.filter((e) => e.conflicts > 0).length,
        exams,
      };
    }),
  }));
}
