import {
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  type SortingState,
  useReactTable,
  type VisibilityState,
} from "@tanstack/react-table";
import { useEffect, useMemo, useState } from "react";
import { createScheduleColumns } from "@/components/schedules/columns";
import type { ScheduleListItem } from "@/lib/api/schedules";
import { useScheduleSelection } from "@/lib/hooks/useScheduleSelection";
import { useSchedulesViewStore } from "@/lib/store/schedulesViewStore";

/** The list opens newest first. */
const DEFAULT_SORTING: SortingState = [{ id: "created_at", desc: true }];

export function useScheduleTable(
  schedules: ScheduleListItem[],
  onDelete?: (scheduleId: string) => void,
) {
  const [sorting, setSorting] = useState<SortingState>(DEFAULT_SORTING);
  const [globalFilter, setGlobalFilter] = useState("");
  const [pageIndex, setPageIndex] = useState(0);
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({});
  const pageSize = useSchedulesViewStore((s) => s.pageSize);
  const { rowSelection, ...selection } = useScheduleSelection();

  const columns = useMemo(() => createScheduleColumns(onDelete), [onDelete]);

  const table = useReactTable({
    data: schedules,
    columns,
    state: {
      sorting,
      globalFilter,
      columnVisibility,
      pagination: { pageIndex, pageSize },
      rowSelection,
    },
    // A new sort or search starts again from the first page.
    onSortingChange: (updater) => {
      setSorting(updater);
      setPageIndex(0);
    },
    onGlobalFilterChange: (value) => {
      setGlobalFilter(value);
      setPageIndex(0);
    },
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    ...selection,
  });

  // Deleting the last schedule of the last page would leave an empty page.
  const pageCount = table.getPageCount();
  useEffect(() => {
    if (pageIndex > 0 && pageIndex >= pageCount) {
      setPageIndex(Math.max(0, pageCount - 1));
    }
  }, [pageIndex, pageCount]);

  return { table, pageIndex, setPageIndex, pageSize };
}
