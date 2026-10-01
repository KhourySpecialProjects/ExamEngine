import type { DatasetMetadata } from "@/lib/types/datasets.api.types";

export interface DatasetGroupWarning {
  kind: "combined" | "common";
  group: string;
  message: string;
}

/**
 * Combined/common exam groups the upload found can never be seated, so the
 * scheduler will leave them unscheduled. Read from the metadata saved with the
 * dataset at upload time.
 */
export function datasetGroupWarnings(
  dataset: DatasetMetadata,
): DatasetGroupWarning[] {
  const combined = (
    dataset.files.combined_exams?.over_capacity_groups ?? []
  ).map(
    (g): DatasetGroupWarning => ({
      kind: "combined",
      group: g.group,
      message: `${g.total_enrollment} students; largest room seats ${g.max_room_capacity}`,
    }),
  );
  const common = (dataset.files.common_exams?.infeasible_groups ?? []).map(
    (g): DatasetGroupWarning => ({
      kind: "common",
      group: g.group,
      message: g.reason,
    }),
  );
  return [...combined, ...common];
}
