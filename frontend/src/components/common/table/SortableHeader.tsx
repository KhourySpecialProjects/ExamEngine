import type { Column } from "@tanstack/react-table";
import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import { Button } from "@/components/ui/button";

interface SortableHeaderProps<TData, TValue> {
  column: Column<TData, TValue>;
  label: string;
}

/**
 * Reusable sortable column header component: click toggles ascending and
 * descending; the arrow shows the current direction.
 */
export function SortableHeader<TData, TValue>({
  column,
  label,
}: SortableHeaderProps<TData, TValue>) {
  if (!column.getCanSort()) return <span>{label}</span>;
  const sorted = column.getIsSorted();
  const Icon =
    sorted === "asc" ? ArrowUp : sorted === "desc" ? ArrowDown : ArrowUpDown;
  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={() => column.toggleSorting(sorted === "asc")}
      className="-ml-3"
    >
      {label}
      <Icon className="ml-2 size-4" />
    </Button>
  );
}
