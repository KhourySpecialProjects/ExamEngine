import type {
  ScheduleDatasetSummary,
  ScheduleListItem,
} from "@/lib/api/schedules";

/** The schedules generated from one dataset. */
export interface ScheduleGroup {
  datasetId: string;
  dataset: ScheduleDatasetSummary;
  /** In the chosen schedule order. */
  schedules: ScheduleListItem[];
  /** created_at of the group's newest schedule. */
  latestRun: string;
}

export type GroupSort = "latest" | "name" | "uploaded";
export type ScheduleSort = "newest" | "oldest" | "name" | "exams";

export const GROUP_SORT_LABELS: Record<GroupSort, string> = {
  latest: "Latest run first",
  name: "Dataset name A–Z",
  uploaded: "Newest upload first",
};

export const SCHEDULE_SORT_LABELS: Record<ScheduleSort, string> = {
  newest: "Newest first",
  oldest: "Oldest first",
  name: "Name A–Z",
  exams: "Most exams first",
};

const byText = (a: string, b: string) =>
  a.localeCompare(b, undefined, { sensitivity: "base", numeric: true });

const SCHEDULE_ORDER: Record<
  ScheduleSort,
  (a: ScheduleListItem, b: ScheduleListItem) => number
> = {
  newest: (a, b) => byText(b.created_at, a.created_at),
  oldest: (a, b) => byText(a.created_at, b.created_at),
  name: (a, b) => byText(a.schedule_name, b.schedule_name),
  exams: (a, b) => b.total_exams - a.total_exams,
};

const GROUP_ORDER: Record<
  GroupSort,
  (a: ScheduleGroup, b: ScheduleGroup) => number
> = {
  latest: (a, b) => byText(b.latestRun, a.latestRun),
  name: (a, b) => byText(a.dataset.name, b.dataset.name),
  uploaded: (a, b) => byText(b.dataset.uploaded_at, a.dataset.uploaded_at),
};

/**
 * Schedules grouped by dataset, groups and schedules in the chosen orders.
 *
 * `search` (case-insensitive) keeps a whole group when its dataset name
 * matches, otherwise only the schedules whose name matches; groups left
 * empty are dropped.
 */
export function groupSchedulesByDataset(
  schedules: readonly ScheduleListItem[],
  {
    search = "",
    groupSort = "latest",
    scheduleSort = "newest",
  }: { search?: string; groupSort?: GroupSort; scheduleSort?: ScheduleSort },
): ScheduleGroup[] {
  const query = search.trim().toLowerCase();
  const byDataset = new Map<string, ScheduleListItem[]>();
  for (const schedule of schedules) {
    const members = byDataset.get(schedule.dataset_id) ?? [];
    members.push(schedule);
    byDataset.set(schedule.dataset_id, members);
  }

  const groups: ScheduleGroup[] = [];
  for (const [datasetId, members] of byDataset) {
    const dataset = members[0].dataset;
    const shown =
      !query || dataset.name.toLowerCase().includes(query)
        ? members
        : members.filter((s) => s.schedule_name.toLowerCase().includes(query));
    if (shown.length === 0) continue;
    groups.push({
      datasetId,
      dataset,
      schedules: [...shown].sort(SCHEDULE_ORDER[scheduleSort]),
      latestRun: members.reduce(
        (latest, s) => (s.created_at > latest ? s.created_at : latest),
        "",
      ),
    });
  }
  return groups.sort(GROUP_ORDER[groupSort]);
}
