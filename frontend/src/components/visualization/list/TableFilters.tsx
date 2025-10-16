import type { Table } from "@tanstack/react-table";
import { ChevronDown, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import type { Exam } from "@/store/calendarStore";

interface TableFiltersProps {
  table: Table<Exam>;
}

/**
 * TableFilters - Search inputs and column visibility controls
 */
export function TableFilters({ table }: TableFiltersProps) {
  return (
    <div className="flex items-center gap-4">
      <SearchInput
        placeholder="Search courses..."
        value={
          (table.getColumn("courseCode")?.getFilterValue() as string) ?? ""
        }
        onChange={(value) =>
          table.getColumn("courseCode")?.setFilterValue(value)
        }
      />
      <SearchInput
        placeholder="Search instructors..."
        value={
          (table.getColumn("instructor")?.getFilterValue() as string) ?? ""
        }
        onChange={(value) =>
          table.getColumn("instructor")?.setFilterValue(value)
        }
      />
      <ColumnVisibilityDropdown table={table} />
    </div>
  );
}

/**
 * SearchInput - Reusable search input with icon
 */
function SearchInput({
  placeholder,
  value,
  onChange,
}: {
  placeholder: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="relative flex-1 max-w-sm">
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
      <Input
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="pl-9"
      />
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
