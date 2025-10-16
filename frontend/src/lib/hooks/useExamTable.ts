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
import { useCalendarStore } from "@/lib/store/calendarStore";
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
  const filters = useCalendarStore((state) => state.filters);

  // Memoize filtered exams based on allExams and filters
  const filteredExams = useMemo(() => {
    return allExams.filter((exam) => {
      if (filters.searchQuery) {
        const query = filters.searchQuery.toLowerCase();
        const matchesSearch =
          exam.courseCode.toLowerCase().includes(query) ||
          exam.instructor.toLowerCase().includes(query) ||
          exam.room.toLowerCase().includes(query);

        if (!matchesSearch) return false;
      }

      if (
        filters.departmentFilter &&
        exam.department !== filters.departmentFilter
      ) {
        return false;
      }

      if (filters.showConflictsOnly && exam.conflicts === 0) {
        return false;
      }

      return true;
    });
  }, [allExams, filters]);

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
