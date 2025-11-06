import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import type { CalendarRow } from "@/lib/store/calendarStore";
import type { CalendarExam, ScheduleResult } from "./api/schedules";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const generateSampleData = (): CalendarRow[] => {
  const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
  const timeSlots = [
    "8:00 - 10:00 AM",
    "10:30 AM - 12:30 PM",
    "1:00 - 3:00 PM",
    "3:30 - 5:30 PM",
    "6:00 - 8:00 PM",
  ];

  const departments = ["CS", "MATH", "PHYS", "CHEM", "EECE", "BUSN"];
  const buildings = ["WVH", "Shillman", "Kariotis", "Ryder", "Churchill"];

  const data: CalendarRow[] = [];

  // Use a simple deterministic "random" function based on timeSlot and day
  const deterministicRandom = (seed: string, max: number) => {
    let hash = 0;
    for (let i = 0; i < seed.length; i++) {
      const char = seed.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32-bit integer
    }
    return Math.abs(hash) % max;
  };

  for (const timeSlot of timeSlots) {
    const row: CalendarRow = {
      timeSlot,
      days: [],
    };

    for (const day of days) {
      const seed = `${timeSlot}-${day}`;
      const examCount = deterministicRandom(seed, 80);
      const conflicts = examCount > 15 ? deterministicRandom(`${seed}-conflicts`, 120) : 0;

      const exams = [];
      for (let i = 0; i < examCount; i++) {
        const examSeed = `${seed}-${i}`;
        const dept = departments[deterministicRandom(examSeed, departments.length)];
        const building = buildings[deterministicRandom(`${examSeed}-building`, buildings.length)];
        exams.push({
          id: `exam-${day}-${timeSlot}-${i}-${deterministicRandom(`${examSeed}-id`, 4000)}`,
          courseCode: `${dept} ${1000 + deterministicRandom(`${examSeed}-course`, 4000)}`,
          section: `0${deterministicRandom(`${examSeed}-section`, 5) + 1}`,
          department: dept,
          instructor: [
            "Dr. Smith",
            "Prof. Johnson",
            "Dr. Williams",
            "Prof. Davis",
          ][deterministicRandom(`${examSeed}-instructor`, 4)],
          studentCount: 50 + deterministicRandom(`${examSeed}-students`, 150),
          room: `${building} ${100 + deterministicRandom(`${examSeed}-room`, 300)}`,
          building: building,
          conflicts: i < conflicts ? deterministicRandom(`${examSeed}-conflict`, 3) + 1 : 0,
          day,
          timeSlot,
        });
      }

      row.days.push({ day, timeSlot, examCount, conflicts, exams });
    }

    data.push(row);
  }

  return data;
};

export function wrapSampleDataAsScheduleResult(
  calendarRows: CalendarRow[],
): ScheduleResult {
  // Convert CalendarRow[] back to calendar structure
  const calendar: Record<string, Record<string, CalendarExam[]>> = {};
  const backendDays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  calendarRows.forEach((row) => {
    row.days.forEach((cell, index) => {
      const backendDay = backendDays[index];
      const timeSlot = row.timeSlot;

      if (!calendar[backendDay]) calendar[backendDay] = {};
      if (!calendar[backendDay][timeSlot]) calendar[backendDay][timeSlot] = [];

      calendar[backendDay][timeSlot] = cell.exams.map((exam) => ({
        CRN: exam.section,
        Course: exam.courseCode,
        Room: exam.room,
        Capacity: 100,
        Size: exam.studentCount,
        Valid: exam.conflicts === 0,
      }));
    });
  });

  const totalExams = calendarRows.reduce(
    (sum, row) =>
      sum + row.days.reduce((daySum, day) => daySum + day.examCount, 0),
    0,
  );

  // Use a deterministic ID instead of Date.now() to avoid hydration mismatch
  return {
    dataset_id: "sample-data",
    dataset_name: "Sample Data",
    summary: {
      num_classes: totalExams,
      num_students: Math.floor(totalExams * 25),
      potential_overlaps: 0,
      real_conflicts: 0,
      num_rooms: 50,
      slots_used: calendarRows.length,
    },
    conflicts: {
      total: 0,
      breakdown: [],
      details: {},
    },
    failures: [],
    schedule: {
      complete: [],
      calendar,
      total_exams: totalExams,
    },
    parameters: {
      max_per_day: 3,
      avoid_back_to_back: true,
      max_days: 7,
    },
  };
}

export const getTimeAgo = (dateString: string) => {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
};
