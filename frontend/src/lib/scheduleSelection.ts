import type { ScheduleListItem } from "@/lib/api/schedules";

/** Most schedules the Compare page shows side by side. */
export const MAX_COMPARED = 4;

/**
 * Why `schedule` can't be picked for Compare, or null if it can. A picked
 * schedule can always be unpicked.
 */
export function selectionBlocker(
  schedule: ScheduleListItem,
  selectedIds: readonly string[],
): string | null {
  if (selectedIds.includes(schedule.schedule_id)) return null;
  if (schedule.status !== "Completed") {
    return "Only completed schedules can be compared";
  }
  if (selectedIds.length >= MAX_COMPARED) {
    return `You can compare up to ${MAX_COMPARED} schedules`;
  }
  return null;
}

/**
 * The picked ids after a table selection change (id → selected), in the
 * order they were picked: kept ids stay in place, new ones go last.
 */
export function nextSelection(
  selectedIds: readonly string[],
  rowSelection: Record<string, boolean>,
): string[] {
  const kept = selectedIds.filter((id) => rowSelection[id]);
  const added = Object.keys(rowSelection).filter(
    (id) => rowSelection[id] && !selectedIds.includes(id),
  );
  return [...kept, ...added];
}

/** Drops picks that are no longer listed or no longer completed. */
export function selectableIds(
  selectedIds: readonly string[],
  schedules: readonly ScheduleListItem[],
): string[] {
  const completed = new Set(
    schedules.filter((s) => s.status === "Completed").map((s) => s.schedule_id),
  );
  return selectedIds.filter((id) => completed.has(id));
}

/** The Compare page for these schedules, in this order. */
export function compareHref(selectedIds: readonly string[]): string {
  return `/dashboard/compare?ids=${selectedIds.map(encodeURIComponent).join(",")}`;
}
