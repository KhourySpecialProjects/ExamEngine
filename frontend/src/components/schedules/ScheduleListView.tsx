"use client";

import { flexRender } from "@tanstack/react-table";
import { Table, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useScheduleTable } from "@/lib/hooks/useScheduleTable";
import { DataTableBody } from "@/components/common/table/DataTableBody";
import { DataTableFilters } from "@/components/common/table/DataTableFilters";
import { DataTablePagination } from "@/components/common/table/DataTablePagination";
import type { ScheduleListItem } from "@/lib/api/schedules";

interface ScheduleListViewProps {
  schedules: ScheduleListItem[];
  onDelete?: (scheduleId: string) => void;
}

export function ScheduleListView({
  schedules,
  onDelete,
}: ScheduleListViewProps) {
  const { table } = useScheduleTable(schedules, onDelete);

  return (
    <div className="space-y-4">
      <DataTableFilters table={table} searchPlaceholder="Search schedules..." />

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
            emptyMessage="No schedules found"
            emptyDescription={
              schedules.length > 0
                ? "Try adjusting your search"
                : "Generate a schedule to get started"
            }
          />
        </Table>
      </div>

      <DataTablePagination table={table} itemName="schedules" />
    </div>
  );
}
