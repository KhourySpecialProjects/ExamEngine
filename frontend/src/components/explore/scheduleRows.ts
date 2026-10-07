import type { WeekExam } from "@/components/exam-week/examWeek";
import { isPersonId } from "@/components/person-exams/PersonIdActions";
import type { ScheduleExam } from "@/lib/api/schedules";

/** The row's trimmed instructor ID; null when blank or "nan". */
export function instructorOf(row: ScheduleExam | undefined): string | null {
  const id = row?.Instructor;
  return isPersonId(id) ? id.trim() : null;
}

/**
 * A row of the schedule's exam list (`schedule.complete`) as Explore shows
 * it, placed in the week drawn with `days` and `blockTimes`. An unscheduled
 * row (blank day and block) is unscheduled; a blank room is no room.
 */
export function weekExam(
  row: ScheduleExam,
  days: string[],
  blockTimes: string[],
): WeekExam {
  const day = days.indexOf(row.Day);
  const block = blockTimes.indexOf(row.Block);
  const placed = day >= 0 && block >= 0;
  return {
    crn: row.CRN,
    course_code: row.Course,
    day: placed ? day : null,
    day_name: placed ? row.Day : null,
    block: placed ? block : null,
    block_time: placed ? row.Block : null,
    room: row.Room || null,
    instructor: instructorOf(row),
    size: row.Size,
  };
}
