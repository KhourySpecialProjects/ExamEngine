import {
  type ColumnFiltersState,
  type SortingState,
  type VisibilityState,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { useMemo, useState } from "react";
import { useCalendarStore } from "@/store/calendarStore";
import { createExamColumns } from "@/components/visualization/list/columns";

/**
 * Custom hook for managing exam table state and logic
 *
 * Handles:
 * - Data fetching from Zustand store
 * - Table state (sorting, filtering, visibility)
 * - TanStack Table configuration
 * - Performance optimization with memoization
 */
export function useExamTable() {
  const allExams = useCalendarStore((state) => state.allExams);
  const getFilteredExams = useCalendarStore((state) => state.getFilteredExams);

  // Memoize filtered exams to prevent unnecessary recalculations
  const filteredExams = useMemo(() => {
    return getFilteredExams();
  }, [getFilteredExams, allExams]);

  // Table state management
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({});

  // Memoize columns to prevent recreation on every render
  const columns = useMemo(() => createExamColumns(), []);

  // Configure TanStack Table
  const table = useReactTable({
    data: filteredExams,
    columns,
    state: {
      sorting,
      columnFilters,
      columnVisibility,
    },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: {
      pagination: {
        pageSize: 25,
      },
    },
    // Performance optimizations
    autoResetPageIndex: false,
    enableRowSelection: false,
  });

  return {
    table,
    allExams,
    filteredExams,
  };
}
