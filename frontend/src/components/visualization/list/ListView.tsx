"use client";

import { flexRender } from "@tanstack/react-table";
import { Table, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useExamTable } from "@/lib/hooks/useExamTable";
import { ExamTableBody } from "./ExamTableBody";
import { TableFilters } from "./TableFilters";
import { TablePagination } from "./TablePagination";

/**
 * ListView - Main table view component
 *
 * Features:
 * - Multi-column search (courses, instructors)
 * - Column sorting (all columns)
 * - Column visibility toggle
 * - Pagination (25 per page)
 * - Empty state handling
 * - Responsive design
 * - Performance optimized
 */
export default function ListView() {
  const { table, allExams } = useExamTable();

  return (
    <div className="space-y-4">
      {/* Search filters and column visibility */}
      <TableFilters table={table} />

      {/* Main data table */}
      <div className="overflow-hidden rounded-xl border bg-card shadow-sm">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id}>
                    {header.isPlaceholder
                      ? null
                      : flexRender(
                          header.column.columnDef.header,
                          header.getContext(),
                        )}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <ExamTableBody
            table={table}
            columnCount={table.getAllColumns().length}
            hasData={allExams.length > 0}
          />
        </Table>
      </div>

      {/* Pagination controls */}
      <TablePagination table={table} />
    </div>
  );
}
