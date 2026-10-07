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
  /** Label of the combined exam (same block, same room) it belongs to. */
  combined?: string | null;
  /** Label of the common exam (same block, different rooms) it belongs to. */
  common?: string | null;
}

/**
 * The exam a section sits as part of: its common group, else its combined
 * group, else itself. Sections of one group are one exam for a person.
 */
function examUnit(exam: WeekExam): string {
  if (exam.common) return `common:${exam.common}`;
  if (exam.combined) return `combined:${exam.combined}`;
  return `crn:${exam.crn}`;
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

/**
 * Keys of the slots holding two or more different exams (a person's
 * double-books); sections of one combined or common group count once.
 */
export function doubleBookedSlots(
  perSlot: Map<string, WeekExam[]>,
): Set<string> {
  return new Set(
    [...perSlot]
      .filter(([, exams]) => new Set(exams.map(examUnit)).size > 1)
      .map(([key]) => key),
  );
}
