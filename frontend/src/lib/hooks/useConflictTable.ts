// frontend/src/lib/hooks/useExamTable.ts
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
import { useScheduleData } from "./useScheduleData";

/**
 * Custom hook for managing exam table state and logic
 *
 * Handles:
 * - Table state (sorting, filtering, visibility)
 * - TanStack Table configuration
 * - Performance optimization with memoization
 */
export function useConflictTable() {
  const { allExams } = useScheduleData();
  const conflict_exams = allExams.filter((e) => e.conflicts > 0)

  // Table state management
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({});

  // Memoize columns to prevent recreation on every render
  const columns = useMemo(() => createExamColumns(), []);

  // Configure TanStack Table
  const table = useReactTable({
    data: allExams,
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
    // Performance optimizations
    autoResetPageIndex: false,
    enableRowSelection: false,
  });

  return {
    table,
    allExams,
  };
}
