import type { Table } from "@tanstack/react-table";
import { ChevronDown, Search, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import type { Exam } from "@/lib/store/calendarStore";

interface TableFiltersProps {
  table: Table<Exam>;
}

/**
 * TableFilters - Search inputs and column visibility controls
 */
export function TableFilters({ table }: TableFiltersProps) {
  const globalFilter = table.getState().globalFilter ?? "";
  return (
    <div className="flex items-center gap-4">
      <div className="relative flex-1 max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
        <Input
          placeholder="Search courses, rooms, instructors, time..."
          value={globalFilter}
          onChange={(e) => table.setGlobalFilter(e.target.value)}
          className="pl-9 pr-9"
        />
        {globalFilter && (
          <Button
            variant="ghost"
            size="icon"
            className="absolute right-1 top-1/2 -translate-y-1/2 h-7 w-7"
            onClick={() => table.setGlobalFilter("")}
          >
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>
      <ColumnVisibilityDropdown table={table} />
    </div>
  );
}

/**
 * ColumnVisibilityDropdown - Toggle column visibility
 */
function ColumnVisibilityDropdown({ table }: { table: Table<Exam> }) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" className="ml-auto">
          Columns <ChevronDown className="ml-2 size-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {table
          .getAllColumns()
          .filter((column) => column.getCanHide())
          .map((column) => (
            <DropdownMenuCheckboxItem
              key={column.id}
              className="capitalize"
              checked={column.getIsVisible()}
              onCheckedChange={(value) => column.toggleVisibility(!!value)}
            >
              {column.id}
            </DropdownMenuCheckboxItem>
          ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
