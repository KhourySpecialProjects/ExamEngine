import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import type { CalendarRow } from "@/lib/types/calendar.type";
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
      hash = (hash << 5) - hash + char;
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
      const conflicts =
        examCount > 15 ? deterministicRandom(`${seed}-conflicts`, 120) : 0;

      const exams = [];
      for (let i = 0; i < examCount; i++) {
        const examSeed = `${seed}-${i}`;
        const dept =
          departments[deterministicRandom(examSeed, departments.length)];
        const building =
          buildings[
            deterministicRandom(`${examSeed}-building`, buildings.length)
          ];
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
          conflicts:
            i < conflicts
              ? deterministicRandom(`${examSeed}-conflict`, 3) + 1
              : 0,
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
  if (Number.isNaN(date.getTime())) {
    return "Invalid date";
  }

  const diffMs = now.getTime() - date.getTime();
  if (diffMs < 0) {
    return "Just now";
  }
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
};

/* ---------- CSV Export Utilities ---------- */

/**
 * Convert an array of record objects to a CSV Blob.
 * Keeps header order from the first object.
 */
export function scheduleRowsToCsvBlob(rows: Record<string, any>[]) {
  if (!rows || rows.length === 0) {
    return new Blob([""], { type: "text/csv;charset=utf-8;" });
  }

  const headers = Object.keys(rows[0]);
  const csvLines = [headers.join(",")];

  for (const r of rows) {
    const values = headers.map((h) => {
      const v = (r as any)[h];
      if (v === null || v === undefined) return "";
      const s = String(v).replace(/"/g, '""');
      return s.includes(",") || s.includes('"') ? `"${s}"` : s;
    });
    csvLines.push(values.join(","));
  }

  const csvContent = csvLines.join("\n");
  return new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
}

export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export function exportScheduleRowsAsCsv(
  rows: Record<string, any>[],
  filename = "schedule_exams.csv",
) {
  const blob = scheduleRowsToCsvBlob(rows);
  downloadBlob(blob, filename);
}

/* ---------- Color / Luminance Utilities ---------- */

export function parseRgbString(bg: string): [number, number, number] {
  if (!bg) return [255, 255, 255];
  // handle rgb() or rgba()
  const rgbMatch = bg.match(/rgba?\(([^)]+)\)/i);
  if (rgbMatch) {
    const parts = rgbMatch[1].split(",").map((p) => Number(p.trim()));
    return [parts[0] || 0, parts[1] || 0, parts[2] || 0];
  }

  // handle hex #rrggbb
  const hexMatch = bg.match(/^#?([a-f0-9]{6})$/i);
  if (hexMatch) {
    const hex = hexMatch[1];
    const r = parseInt(hex.slice(0, 2), 16);
    const g = parseInt(hex.slice(2, 4), 16);
    const b = parseInt(hex.slice(4, 6), 16);
    return [r, g, b];
  }

  // fallback: try to extract digits
  const nums = bg.match(/\d+/g)?.map(Number) || [255, 255, 255];
  return [nums[0] || 255, nums[1] || 255, nums[2] || 255];
}

export function getLuminanceFromRgb(rgb: [number, number, number]) {
  const [r, g, b] = rgb;
  return 0.299 * r + 0.587 * g + 0.114 * b;
}

export function getReadableTextColorFromBg(bg: string) {
  const rgb = parseRgbString(bg);
  const lum = getLuminanceFromRgb(rgb);
  return lum > 160 ? "#0f172a" : "#ffffff";
}
