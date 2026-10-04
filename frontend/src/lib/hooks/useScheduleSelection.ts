import type {
  OnChangeFn,
  Row,
  RowSelectionState,
  TableMeta,
} from "@tanstack/react-table";
import { useMemo } from "react";
import type { ScheduleListItem } from "@/lib/api/schedules";
import { nextSelection, selectionBlocker } from "@/lib/scheduleSelection";
import { useSchedulesViewStore } from "@/lib/store/schedulesViewStore";

/**
 * Row-selection options for a schedules table. Every table (the list and each
 * dataset card) shares the picks in the schedules view store, so they survive
 * paging, searching, sorting and switching views.
 */
export function useScheduleSelection() {
  const selectedIds = useSchedulesViewStore((s) => s.selectedIds);
  const setSelectedIds = useSchedulesViewStore((s) => s.setSelectedIds);

  const rowSelection = useMemo<RowSelectionState>(
    () => Object.fromEntries(selectedIds.map((id) => [id, true])),
    [selectedIds],
  );
  const onRowSelectionChange: OnChangeFn<RowSelectionState> = (updater) =>
    setSelectedIds(
      nextSelection(
        selectedIds,
        typeof updater === "function" ? updater(rowSelection) : updater,
      ),
    );
  const meta: TableMeta<ScheduleListItem> = {
    selectionBlocker: (schedule) => selectionBlocker(schedule, selectedIds),
  };

  return {
    rowSelection,
    onRowSelectionChange,
    getRowId: (schedule: ScheduleListItem) => schedule.schedule_id,
    enableRowSelection: (row: Row<ScheduleListItem>) =>
      selectionBlocker(row.original, selectedIds) === null,
    meta,
  };
}
