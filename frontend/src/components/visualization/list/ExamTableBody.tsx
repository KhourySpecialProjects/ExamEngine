import { flexRender } from "@tanstack/react-table";
import type { Table } from "@tanstack/react-table";
import type { Exam } from "@/lib/store/calendarStore";
import { TableBody, TableCell, TableRow } from "@/components/ui/table";
import { EmptyState } from "./EmptyState";

interface ExamTableBodyProps {
  table: Table<Exam>;
  columnCount: number;
  hasData: boolean;
}

/**
 * ExamTableBody - Renders table rows or empty state
 */
export function ExamTableBody({
  table,
  columnCount,
  hasData,
}: ExamTableBodyProps) {
  const rows = table.getRowModel().rows;

  if (rows.length === 0) {
    return (
      <TableBody>
        <TableRow>
          <TableCell colSpan={columnCount} className="p-0">
            <EmptyState hasData={hasData} />
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
