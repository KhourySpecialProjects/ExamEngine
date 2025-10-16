import type { Table } from "@tanstack/react-table";
import type { Exam } from "@/lib/store/calendarStore";
import { Button } from "@/components/ui/button";

interface TablePaginationProps {
  table: Table<Exam>;
}

/**
 * TablePagination - Pagination controls with row counts
 */
export function TablePagination({ table }: TablePaginationProps) {
  const { pageIndex, pageSize } = table.getState().pagination;
  const totalRows = table.getFilteredRowModel().rows.length;
  const startRow = pageIndex * pageSize + 1;
  const endRow = Math.min((pageIndex + 1) * pageSize, totalRows);

  return (
    <div className="flex items-center justify-between">
      <div className="text-sm text-muted-foreground">
        Showing <span className="font-medium text-foreground">{startRow}</span>{" "}
        to <span className="font-medium text-foreground">{endRow}</span> of{" "}
        <span className="font-medium text-foreground">{totalRows}</span> exams
      </div>
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => table.previousPage()}
          disabled={!table.getCanPreviousPage()}
        >
          Previous
        </Button>
        <div className="text-sm text-muted-foreground">
          Page{" "}
          <span className="font-medium text-foreground">{pageIndex + 1}</span>{" "}
          of{" "}
          <span className="font-medium text-foreground">
            {table.getPageCount()}
          </span>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => table.nextPage()}
          disabled={!table.getCanNextPage()}
        >
          Next
        </Button>
      </div>
    </div>
  );
}
