import type { Table } from "@tanstack/react-table";
import { flexRender } from "@tanstack/react-table";
import { AlertCircle } from "lucide-react";
import { TableBody, TableCell, TableRow } from "@/components/ui/table";

interface DataTableBodyProps<TData> {
  table: Table<TData>;
  columnCount: number;
  emptyMessage?: string;
  emptyDescription?: string;
}

/**
 * Generic reusable table body component
 * Renders table rows or empty state
 */
export function DataTableBody<TData>({
  table,
  columnCount,
  emptyMessage = "No results found",
  emptyDescription = "Try adjusting your search or filters",
}: DataTableBodyProps<TData>) {
  const rows = table.getRowModel().rows;

  if (rows.length === 0) {
    return (
      <TableBody>
        <TableRow>
          <TableCell colSpan={columnCount} className="h-24 text-center">
            <div className="flex flex-col items-center justify-center gap-3 text-muted-foreground h-[400px]">
              <div className="rounded-full bg-muted p-4">
                <AlertCircle className="size-8" />
              </div>
              <div className="space-y-1 text-center">
                <p className="text-sm font-medium">{emptyMessage}</p>
                <p className="text-sm">{emptyDescription}</p>
              </div>
            </div>
          </TableCell>
        </TableRow>
      </TableBody>
    );
  }

  return (
    <TableBody>
      {rows.map((row) => (
        <TableRow key={row.id} className="hover:bg-muted/50 transition-colors">
          {row.getVisibleCells().map((cell) => (
            <TableCell key={cell.id}>
              {flexRender(cell.column.columnDef.cell, cell.getContext())}
            </TableCell>
          ))}
        </TableRow>
      ))}
    </TableBody>
  );
}
