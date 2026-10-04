"use client";

import { flexRender } from "@tanstack/react-table";
import { DataTableBody } from "@/components/common/table/DataTableBody";
import { DataTableFilters } from "@/components/common/table/DataTableFilters";
import { PaginationBar } from "@/components/common/table/PaginationBar";
import { Table, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { ScheduleListItem } from "@/lib/api/schedules";
import { useScheduleTable } from "@/lib/hooks/useScheduleTable";
import { useSchedulesViewStore } from "@/lib/store/schedulesViewStore";

interface ScheduleListViewProps {
  schedules: ScheduleListItem[];
  onDelete?: (scheduleId: string) => void;
}

export function ScheduleListView({
  schedules,
  onDelete,
}: ScheduleListViewProps) {
  const { table, pageIndex, setPageIndex, pageSize } = useScheduleTable(
    schedules,
    onDelete,
  );
  const setPageSize = useSchedulesViewStore((s) => s.setPageSize);
  const bar = {
    page: pageIndex,
    pageSize,
    total: table.getFilteredRowModel().rows.length,
    noun: " schedules",
    onPage: setPageIndex,
  };

  return (
    <div className="space-y-4">
      <DataTableFilters table={table} searchPlaceholder="Search schedules..." />

      <PaginationBar
        {...bar}
        onPageSize={(size) => {
          setPageSize(size);
          setPageIndex(0);
        }}
      />

      <div className="overflow-hidden rounded-xl border bg-card shadow-sm">
        {/* Fixed layout with percentage widths: columns keep their place
            from page to page and still scale with the window. */}
        <Table className="min-w-[960px] table-fixed">
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead
                    key={header.id}
                    className={header.column.columnDef.meta?.width}
                    aria-sort={
                      header.column.getIsSorted() === "asc"
                        ? "ascending"
                        : header.column.getIsSorted() === "desc"
                          ? "descending"
                          : undefined
                    }
                  >
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
            cellClassName="whitespace-normal break-words"
            emptyMessage="No schedules found"
            emptyDescription={
              schedules.length > 0
                ? "Try adjusting your search"
                : "Generate a schedule to get started"
            }
          />
        </Table>
      </div>

      <PaginationBar {...bar} />
    </div>
  );
}
