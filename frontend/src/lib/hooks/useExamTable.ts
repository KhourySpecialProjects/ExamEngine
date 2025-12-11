import {
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  type Row,
  type SortingState,
  useReactTable,
  type VisibilityState,
} from "@tanstack/react-table";
import { useMemo, useState } from "react";
import { createExamColumns } from "@/components/visualization/list/columns";
import type { Exam } from "../types/calendar.types";
import { useScheduleData } from "./useScheduleData";
import { useCourseMerges } from "./useCourseMerges";

/**
 * Custom global filter function that searches ALL exam fields
 */
function examGlobalFilterFn(
  row: Row<Exam>,
  _columnId: string,
  filterValue: string,
): boolean {
  const search = filterValue.toLowerCase();
  const exam = row.original;

  const searchableFields = [
    exam.courseCode,
    exam.section,
    exam.department,
    exam.instructor,
    exam.room,
    exam.building,
    exam.day,
    exam.timeSlot,
    exam.studentCount?.toString(),
  ];

  return searchableFields.some(
    (field) => field && String(field).toLowerCase().includes(search),
  );
}

/**
 * Custom hook for managing exam table state and logic
 *
 * Handles:
 * - Table state (sorting, filtering, visibility)
 * - TanStack Table configuration
 * - Performance optimization with memoization
 */
export function useExamTable() {
  const { allExams, schedule } = useScheduleData();
  const { isMerged } = useCourseMerges(schedule?.dataset_id);

  // Table state management
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({});
  const [globalFilter, setGlobalFilter] = useState("");

  // Memoize columns to prevent recreation on every render
  const columns = useMemo(() => createExamColumns(isMerged), [isMerged]);

  // Configure TanStack Table
  const table = useReactTable({
    data: allExams,
    columns,
    state: {
      sorting,
      columnVisibility,
      globalFilter,
    },
    onSortingChange: setSorting,
    onColumnVisibilityChange: setColumnVisibility,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: {
      pagination: {
        pageSize: 10,
      },
    },
    globalFilterFn: examGlobalFilterFn,
    // Performance optimizations
    autoResetPageIndex: false,
    enableRowSelection: false,
  });

  return {
    table,
    allExams,
  };
}
