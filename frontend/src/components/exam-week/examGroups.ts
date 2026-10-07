import type { WeekExam } from "./examWeek";

/** A dataset's combined and common exams, looked up by CRN. */
export interface ExamGroups {
  /** CRN -> combined group label. */
  combined: Map<string, string>;
  /** CRN -> common group label. */
  common: Map<string, string>;
  /** Common group label -> its CRNs (with whole combined groups pulled in). */
  commonCrns: Map<string, string[]>;
}

export const NO_GROUPS: ExamGroups = {
  combined: new Map(),
  common: new Map(),
  commonCrns: new Map(),
};

/**
 * Index the dataset's stored groups (label -> CRNs). A combined exam with
 * any CRN listed in a common group belongs to that group as a whole (the
 * rule `useCommonExams` and the scheduler apply).
 */
export function buildExamGroups(
  merges: Record<string, string[]>,
  commonGroups: Record<string, string[]>,
): ExamGroups {
  const crnsOf = (group: unknown) =>
    Array.isArray(group) ? group.map((crn) => String(crn).trim()) : [];
  const combined = new Map<string, string>();
  for (const [label, group] of Object.entries(merges)) {
    for (const crn of crnsOf(group)) combined.set(crn, label);
  }
  const common = new Map<string, string>();
  for (const [label, group] of Object.entries(commonGroups)) {
    for (const crn of crnsOf(group)) common.set(crn, label);
  }
  for (const group of Object.values(merges)) {
    const members = crnsOf(group);
    const label = members.map((crn) => common.get(crn)).find(Boolean);
    if (label) for (const crn of members) common.set(crn, label);
  }
  const commonCrns = new Map<string, string[]>();
  for (const [crn, label] of common) {
    commonCrns.set(label, [...(commonCrns.get(label) ?? []), crn]);
  }
  return { combined, common, commonCrns };
}

/** The exam with its combined and common group labels filled in. */
export function withGroups(exam: WeekExam, groups: ExamGroups): WeekExam {
  const crn = exam.crn.trim();
  return {
    ...exam,
    combined: groups.combined.get(crn) ?? null,
    common: groups.common.get(crn) ?? null,
  };
}
