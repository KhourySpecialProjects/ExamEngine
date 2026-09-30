import { useMemo } from "react";
import type {
  ScheduleExam,
  ScheduleResult,
  UnscheduledGroup,
} from "@/lib/api/schedules";
import { useCommonExams } from "@/lib/hooks/useCommonExams";
import { useCourseMerges } from "@/lib/hooks/useCourseMerges";
import { useDatasetStore } from "@/lib/store/datasetStore";
import type { RoomBlockoutsFileMetadata } from "@/lib/types/datasets.api.types";

const DAY_ORDER = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];

/** An exam named in a problem card. */
export interface ExamIssue {
  crn: string;
  course: string;
  size: number;
}

export interface OverCapacityExam extends ExamIssue {
  room: string;
  capacity: number;
}

export interface GroupStats {
  groups: number;
  /** Scheduled exams (CRNs) that belong to a group. */
  sections: number;
  /** Enrollment summed over those sections. */
  students: number;
}

export interface ScheduleStats {
  totalExams: number;
  /** Exams with a day, a time and a room. */
  placedExams: number;
  /** Unique students from the dataset's enrollments file; null when unknown. */
  uniqueStudents: number | null;
  roomsUsed: number;
  /** Mean seats filled per placed exam, capped at 100% per exam (0-100). */
  roomUtilization: number;
  /** Distinct (day, block) pairs holding at least one exam. */
  slotsUsed: number;
  /** No day, time or room. */
  unscheduled: {
    exams: ExamIssue[];
    students: number;
    /** Groups the scheduler reported, with its reason. */
    groups: UnscheduledGroup[];
    /** Unscheduled CRNs no reported group explains (e.g. older schedules). */
    otherCrns: string[];
  };
  /** A day and time but no room (every fitting room was blocked). */
  unroomed: { exams: ExamIssue[]; students: number };
  /** Placed in a room with fewer seats than students. */
  overCapacity: OverCapacityExam[];
  combined: GroupStats;
  common: GroupStats;
  blockouts: { rooms: number; slots: number };
  perDay: { name: string; exams: number; students: number }[];
  perBlock: { name: string; exams: number }[];
}

export interface ScheduleStatsInput {
  exams: ScheduleExam[];
  uniqueStudents: number | null;
  unscheduledGroups: UnscheduledGroup[];
  combinedGroupCount: number;
  isCombined: (crn: string) => boolean;
  commonGroupCount: number;
  isCommon: (crn: string) => boolean;
  blockouts?: Pick<
    RoomBlockoutsFileMetadata,
    "unique_rooms_blocked" | "total_blockout_entries"
  >;
}

function dayRank(day: string): number {
  const i = DAY_ORDER.indexOf(day);
  return i === -1 ? DAY_ORDER.length : i;
}

/** Minutes after midnight of "9AM" / "11:30AM" / "4:30 PM"; null if none. */
function startMinutes(label: string): number | null {
  const m = /(\d{1,2})(?::(\d{2}))?\s*([AP])M/i.exec(label);
  if (!m) return null;
  const hour = (Number(m[1]) % 12) + (m[3].toUpperCase() === "P" ? 12 : 0);
  return hour * 60 + Number(m[2] ?? 0);
}

/**
 * Block labels come as "0 (9AM-11AM)" (generate) or "9AM-11AM" (saved
 * schedules): order by block number when given, else by start time.
 */
function blockRank(label: string): number {
  const leading = /^\s*(\d+)\b(?!\s*:)(?!\s*[AP]M)/i.exec(label);
  if (leading) return Number(leading[1]);
  return startMinutes(label) ?? Number.POSITIVE_INFINITY;
}

function toIssue(exam: ScheduleExam): ExamIssue {
  return {
    crn: String(exam.CRN),
    course: exam.Course || "",
    size: Number(exam.Size) || 0,
  };
}

const sumSizes = (issues: ExamIssue[]) =>
  issues.reduce((total, e) => total + e.size, 0);

function groupStats(
  exams: ScheduleExam[],
  groups: number,
  inGroup: (crn: string) => boolean,
): GroupStats {
  const members = exams.filter((e) => inGroup(String(e.CRN)));
  return {
    groups,
    sections: members.length,
    students: members.reduce((t, e) => t + (Number(e.Size) || 0), 0),
  };
}

/** Every number on the Statistics tab, from the schedule's exam list. */
export function computeScheduleStats(input: ScheduleStatsInput): ScheduleStats {
  const { exams } = input;
  const unscheduled: ExamIssue[] = [];
  const unroomed: ExamIssue[] = [];
  const overCapacity: OverCapacityExam[] = [];
  const rooms = new Set<string>();
  const slots = new Set<string>();
  const perDay = new Map<string, { exams: number; students: number }>();
  const perBlock = new Map<string, number>();
  let utilizationTotal = 0;
  let utilizationCount = 0;

  for (const exam of exams) {
    if (!exam.Day) {
      unscheduled.push(toIssue(exam));
      continue;
    }
    slots.add(`${exam.Day}\u0000${exam.Block}`);
    if (!exam.Room) {
      unroomed.push(toIssue(exam));
      continue;
    }

    const size = Number(exam.Size) || 0;
    const capacity = Number(exam.Capacity) || 0;
    rooms.add(exam.Room);
    const day = perDay.get(exam.Day) ?? { exams: 0, students: 0 };
    day.exams += 1;
    day.students += size;
    perDay.set(exam.Day, day);
    perBlock.set(exam.Block, (perBlock.get(exam.Block) ?? 0) + 1);
    if (capacity > 0) {
      utilizationTotal += Math.min(size / capacity, 1) * 100;
      utilizationCount += 1;
      if (size > capacity) {
        overCapacity.push({ ...toIssue(exam), room: exam.Room, capacity });
      }
    }
  }

  const grouped = new Set(input.unscheduledGroups.flatMap((g) => g.crns));

  return {
    totalExams: exams.length,
    placedExams: exams.length - unscheduled.length - unroomed.length,
    uniqueStudents: input.uniqueStudents,
    roomsUsed: rooms.size,
    roomUtilization:
      utilizationCount > 0
        ? Math.round((utilizationTotal / utilizationCount) * 10) / 10
        : 0,
    slotsUsed: slots.size,
    unscheduled: {
      exams: unscheduled,
      students: sumSizes(unscheduled),
      groups: input.unscheduledGroups,
      otherCrns: unscheduled.map((e) => e.crn).filter((c) => !grouped.has(c)),
    },
    unroomed: { exams: unroomed, students: sumSizes(unroomed) },
    overCapacity: overCapacity.sort(
      (a, b) => b.size - b.capacity - (a.size - a.capacity),
    ),
    combined: groupStats(exams, input.combinedGroupCount, input.isCombined),
    common: groupStats(exams, input.commonGroupCount, input.isCommon),
    blockouts: {
      rooms: input.blockouts?.unique_rooms_blocked ?? 0,
      slots: input.blockouts?.total_blockout_entries ?? 0,
    },
    perDay: [...perDay]
      .map(([name, d]) => ({ name, ...d }))
      .sort((a, b) => dayRank(a.name) - dayRank(b.name)),
    perBlock: [...perBlock]
      .map(([name, count]) => ({ name, exams: count }))
      .sort((a, b) => blockRank(a.name) - blockRank(b.name)),
  };
}

/** Statistics for a schedule, or null when there is none. */
export function useScheduleStats(
  schedule: ScheduleResult | null | undefined,
): ScheduleStats | null {
  const datasets = useDatasetStore((s) => s.datasets);
  const { merges, isMerged } = useCourseMerges(schedule?.dataset_id);
  const { commonGroups, isCommon } = useCommonExams(
    schedule?.dataset_id,
    merges,
  );

  return useMemo(() => {
    if (!schedule) return null;
    const files = datasets.find(
      (d) => d.dataset_id === schedule.dataset_id,
    )?.files;
    return computeScheduleStats({
      exams: schedule.schedule.complete,
      uniqueStudents: files?.enrollments?.unique_students ?? null,
      unscheduledGroups: schedule.unscheduled_groups ?? [],
      combinedGroupCount: Object.keys(merges).length,
      isCombined: isMerged,
      commonGroupCount: Object.keys(commonGroups).length,
      isCommon,
      blockouts: files?.room_blockouts,
    });
  }, [schedule, datasets, merges, isMerged, commonGroups, isCommon]);
}
