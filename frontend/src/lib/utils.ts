import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import type { CalendarRow } from "@/lib/store/calendarStore";
import type { CalendarExam, ScheduleResult } from "./api/schedules";
import { useScheduleStore } from "@/lib/store/scheduleStore";
import type { conflictMap } from "./types/conflict.types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}



export const conflictMapper = (): conflictMap[] => {
  const { currentSchedule } = useScheduleStore();

  const conflicts = currentSchedule?.conflicts.breakdown
  
  const conflictMap: conflictMap[] = (conflicts ?? []).map((conflict) => ({
    conflictType: conflict.conflict_type,
    backToBack: conflict.conflict_type ? "back_to_back" : false,
    instructorConflicts: conflict.conflict_type
   
  }));

  return conflictMap;
}






export function mapConflictsToConflictMap(breakdown: any[] = []): conflictMap[] {
  const BACK_TO_BACK_TYPES = new Set([
    "back_to_back",
    "back_to_back_student",
    "back_to_back_instructor",
  ]);

  return (breakdown ?? []).map((conf) => {
    const type = conf.conflict_type ?? conf.violation ?? "unknown";

    // Try to extract numeric counts if backend provides them; otherwise default heuristics
    const instructorConflicts =
      typeof conf.instructor_conflicts === "number"
        ? conf.instructor_conflicts
        : conf.instructor_id
        ? 1
        : 0;

    const studentConflicts =
      typeof conf.student_conflicts === "number"
        ? conf.student_conflicts
        : conf.student_id
        ? 1
        : 0;

    return {
      conflictType: type,
      instructorConflicts,
      studentConflicts,
      backToBack: BACK_TO_BACK_TYPES.has(type),
      instructorBackToBack: type === "back_to_back_instructor",
      overMaxExams:
        type === "student_gt_max_per_day" ||
        type === "student_gt3_per_day" ||
        type === "student_gt_max",
    } as conflictMap;
  });
}

/**
 * Build rows for ConflictView tables from backend breakdown and available exams.
 * Returns an object with backRows, largeRows and notScheduledRows arrays.
 */
export function mapConflictsToRows(allExams: any[] = [], breakdown: any[] = []) {
  const annotatedByCrn = new Map<string, any[]>();
  const annotatedByCourse = new Map<string, any[]>();

  const normalizeCourse = (s: any) => {
    if (!s) return null;
    let str = String(s);
    const match = str.match(/course_ref\s+(\S+)/i);
    if (match) return match[1];
    return str.replace(/Name:\s*\d+,\s*dtype:\s*\w+.*/i, "").trim() || null;
  };

  for (const ex of allExams ?? []) {
    const crn = (ex.crn ?? ex.CRN ?? ex.section ?? ex.id)?.toString?.();
    const course = normalizeCourse(ex.course ?? ex.course_name ?? ex.course_ref ?? ex.title);
    if (crn) {
      annotatedByCrn.set(crn, (annotatedByCrn.get(crn) ?? []).concat(ex));
    }
    if (course) {
      annotatedByCourse.set(course, (annotatedByCourse.get(course) ?? []).concat(ex));
    }
  }

  const backRows: Array<any> = [];
  const largeRows: Array<any> = [];
  const notScheduledRows: Array<any> = [];

  for (const conf of breakdown ?? []) {
    const type = conf.conflict_type ?? conf.violation ?? "unknown";
    const crn = conf.crn ?? (Array.isArray(conf.conflicting_crns) && conf.conflicting_crns[0]) ?? null;
    const course = conf.course ?? conf.course_ref ?? conf.conflicting_course ?? null;
    const normCourse = normalizeCourse(course);

    // find matching exams
    const matched: any[] = [];
    if (crn && annotatedByCrn.has(String(crn))) matched.push(...(annotatedByCrn.get(String(crn)) ?? []));
    if (normCourse && annotatedByCourse.has(normCourse)) matched.push(...(annotatedByCourse.get(normCourse) ?? []));

    // include conflicting_courses/conflicting_crns also
    const otherCourses = conf.conflicting_courses ?? conf.conflicting_course ?? null;
    const otherCrns = conf.conflicting_crns ?? conf.conflicting_crn ?? null;
    const addFromList = (list: any) => {
      if (!list) return;
      if (Array.isArray(list)) {
        for (const it of list) {
          const k = String(it);
          if (annotatedByCrn.has(k)) matched.push(...(annotatedByCrn.get(k) ?? []));
          const norm = normalizeCourse(it);
          if (norm && annotatedByCourse.has(norm)) matched.push(...(annotatedByCourse.get(norm) ?? []));
        }
      } else {
        const norm = normalizeCourse(list);
        if (norm && annotatedByCourse.has(norm)) matched.push(...(annotatedByCourse.get(norm) ?? []));
      }
    };
    addFromList(otherCourses);
    addFromList(otherCrns);

    // dedupe
    const uniq = Array.from(new Set(matched));

    // back-to-back rows
    if (type === "back_to_back" || type === "back_to_back_student" || type === "back_to_back_instructor") {
      const studentId = conf.entity_id ?? conf.student_id ?? null;
      const day = conf.day ?? conf.block_day ?? conf.block_time ?? "—";
      const blocks = conf.blocks ?? (conf.block_time ? [conf.block_time] : undefined);
      backRows.push({ student: studentId ? String(studentId) : `student(s): ${conf.count ?? 1}`, day, blocks });
    }

    // large courses not early
    if (type === "large_course_not_early" || conf.large_courses_not_early) {
      if (uniq.length > 0) {
        for (const ex of uniq) {
          largeRows.push({
            crn: ex.crn ?? ex.CRN ?? ex.section ?? "—",
            course: ex.course_name ?? ex.course ?? ex.title ?? "—",
            size: ex.enrollment ?? ex.size ?? ex.students_count ?? "—",
            day: ex.day ?? ex.scheduled_day ?? conf.day ?? "—",
            block: ex.block ?? ex.scheduled_block ?? conf.block_time ?? "—",
          });
        }
      } else {
        largeRows.push({ crn: conf.crn ?? "—", course: conf.course ?? "—", size: conf.size ?? "—", day: conf.day ?? "—", block: conf.block_time ?? "—" });
      }
    }

    // not scheduled — conflicts that reference courses not in allExams or explicit not_scheduled flag
    const unscheduled = conf.not_scheduled || conf.unscheduled_reason || (!uniq.length && (type === "unknown" || type === "course_not_scheduled"));
    if (unscheduled && uniq.length === 0) {
      notScheduledRows.push({ crn: conf.crn ?? conf.course ?? "—", course: conf.course ?? conf.conflicting_course ?? "—", size: conf.size ?? "—", reason: conf.unscheduled_reason ?? `Conflict: ${type}` });
    }
  }

  return { backRows, largeRows, notScheduledRows };
}


/*

export interface ConflictBreakdown {
  student_id?: string;
  entity_id?: string;
  day: string;
  block?: number;
  block_time?: string;
  conflict_type: string;
  blocks?: number[];
  crn?: string;
  course?: string;
  conflicting_crn?: string;
  conflicting_course?: string;
  conflicting_crns?: string[];
  conflicting_courses?: string[];
}

export interface ScheduleFailure {
  CRN: string;
  Course: string;
  Size: number;
  reasons: Record<string, number>;
}

export interface ScheduleExam {
  CRN: string;
  Course: string;
  Day: string;
  Block: string;
  Room: string;
  Capacity: number;
  Size: number;
  Valid: boolean;
  Instructor?: string;
}

export interface CalendarExam {
  CRN: string;
  Course: string;
  Room: string;
  Capacity: number;
  Size: number;
  Valid: boolean;
  Instructor?: string;
}

export interface CalendarData {
  [day: string]: {
    [timeSlot: string]: CalendarExam[];
  };
}

export interface ScheduleSummary {
  num_classes: number;
  num_students: number;
  potential_overlaps: number;
  real_conflicts: number;
  num_rooms: number;
  slots_used: number;
}

export interface ScheduleConflicts {
  total: number;
  breakdown: ConflictBreakdown[];
  details: Record<string, string[]>;
}

export interface ScheduleData {
  complete: ScheduleExam[];
  calendar: CalendarData;
  total_exams: number;
}

export interface ScheduleResult {
  dataset_id: string;
  dataset_name: string;
  summary: ScheduleSummary;
  conflicts: ScheduleConflicts;
  failures: ScheduleFailure[];
  schedule: ScheduleData;
  parameters: ScheduleParameters;
}

*/






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
  } as any;
  };

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
