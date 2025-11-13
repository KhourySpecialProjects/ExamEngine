import { useMemo, useState } from "react";
import { createScheduleColumns } from "@/components/schedules/columns";
import type { ScheduleListItem } from "@/lib/api/schedules";
import {
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  SortingState,
  useReactTable,
  VisibilityState,
} from "@tanstack/react-table";

export function useScheduleTable(
  schedules: ScheduleListItem[],
  onDelete?: (scheduleId: string) => void,
) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({});

  const columns = useMemo(() => createScheduleColumns(onDelete), [onDelete]);

  const table = useReactTable({
    data: schedules,
    columns,
    state: {
      sorting,
      columnVisibility,
    },
    onSortingChange: setSorting,
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: {
      pagination: {
        pageSize: 10,
      },
    },
    autoResetPageIndex: false,
    enableRowSelection: false,
  });

  return {
    table,
    schedules,
  };
}
