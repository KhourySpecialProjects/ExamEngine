import type { PersonExam } from "@/lib/api/schedules";

/**
 * An exam as the exam list and week grid show it. Day, block and room are
 * null when it is unscheduled (room also when no room was free).
 */
export interface WeekExam extends PersonExam {
  /** A late-add candidate that is not in the schedule (drawn dashed). */
  proposed?: boolean;
  instructor?: string | null;
  size?: number | null;
}

/** Key of a (day, block) slot. */
export function slotKey(day: number, block: number): string {
  return `${day}-${block}`;
}

export function slotOf(exam: PersonExam): string | null {
  return exam.day != null && exam.block != null
    ? slotKey(exam.day, exam.block)
    : null;
}

/** By day and block, then unscheduled; proposed last in its block; then CRN. */
export function byWeek(a: WeekExam, b: WeekExam): number {
  return (
    Number(a.day == null) - Number(b.day == null) ||
    (a.day ?? 0) - (b.day ?? 0) ||
    (a.block ?? 0) - (b.block ?? 0) ||
    Number(!!a.proposed) - Number(!!b.proposed) ||
    a.crn.localeCompare(b.crn)
  );
}

/** Scheduled exams by slot key, in the given order. */
export function examsBySlot(exams: WeekExam[]): Map<string, WeekExam[]> {
  const perSlot = new Map<string, WeekExam[]>();
  for (const exam of exams) {
    const slot = slotOf(exam);
    if (slot) perSlot.set(slot, [...(perSlot.get(slot) ?? []), exam]);
  }
  return perSlot;
}

/** Keys of the slots holding two or more of `exams` (a person's double-books). */
export function doubleBookedSlots(
  perSlot: Map<string, WeekExam[]>,
): Set<string> {
  return new Set(
    [...perSlot].filter(([, exams]) => exams.length > 1).map(([key]) => key),
  );
}
