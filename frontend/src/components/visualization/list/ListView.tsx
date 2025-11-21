"use client";

import { flexRender } from "@tanstack/react-table";
import { DataTableBody } from "@/components/common/table/DataTableBody";
import { DataTableFilters } from "@/components/common/table/DataTableFilters";
import { DataTablePagination } from "@/components/common/table/DataTablePagination";
import { Table, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useExamTable } from "@/lib/hooks/useExamTable";

export default function ListView() {
  const { table, allExams } = useExamTable();

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <div className="pl-2">
          <h1 className="text-2xl font-bold">List View</h1>
          <p className="text-muted-foreground">
            Searchable table of all scheduled exams
          </p>
        </div>
      </div>

      <DataTableFilters table={table} searchPlaceholder="Search exams..." />

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
          <DataTableBody
            table={table}
            columnCount={table.getAllColumns().length}
            emptyMessage="No exams found"
            emptyDescription={
              allExams.length > 0
                ? "Try adjusting your search or filters"
                : "Upload a dataset to get started"
            }
          />
        </Table>
      </div>

      <DataTablePagination table={table} itemName="exams" />
    </div>
  );
}
