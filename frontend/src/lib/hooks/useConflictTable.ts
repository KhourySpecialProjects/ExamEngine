// frontend/src/lib/hooks/useConflictTable.ts
// Custom hook for managing conflict-related table data and TanStack table wiring.
// This consolidates conflict-specific table logic and provides a memoized
// list of exams that have conflicts (conflictExams).
import {
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  type SortingState,
  useReactTable,
  type VisibilityState,
} from "@tanstack/react-table";
import { useMemo, useState } from "react";
import { createExamColumns } from "@/components/visualization/list/columns";
import { useScheduleData } from "@/lib/hooks/useScheduleData";

/**
 * useConflictTable
 * - provides a TanStack `table` configured for conflict-related exam rows
 * - returns `conflictExams` (memoized) and `allExams` for callers that need full data
 */
export function useConflictTable() {
  const { allExams = [] } = useScheduleData();

  const conflictExams = useMemo(() => {
    if (!Array.isArray(allExams)) return [];
    return allExams.filter((e: any) => {
      const n = e?.conflicts ?? e?.conflict_count ?? e?.conflicts_count ?? 0;
      return Number(n || 0) > 0;
    });
  }, [allExams]);

  // Table state
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({});

  const columns = useMemo(() => createExamColumns(), []);

  const table = useReactTable({
    data: conflictExams,
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
      pagination: { pageSize: 10 },
    },
    autoResetPageIndex: false,
    enableRowSelection: false,
  });

  return { table, allExams, conflictExams };
}
