import type { Column } from "@tanstack/react-table";
import { ArrowUpDown } from "lucide-react";
import { Button } from "@/components/ui/button";

interface SortableHeaderProps<TData, TValue> {
  column: Column<TData, TValue>;
  label: string;
}

/**
 * Reusable sortable column header component
 */
export function SortableHeader<TData, TValue>({
  column,
  label,
}: SortableHeaderProps<TData, TValue>) {
  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
      className="-ml-3"
    >
      {label}
      <ArrowUpDown className="ml-2 size-4" />
    </Button>
  );
}
