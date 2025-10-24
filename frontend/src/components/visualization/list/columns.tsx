import {
  type Column,
  type ColumnDef,
  createColumnHelper,
} from "@tanstack/react-table";
import { AlertCircle, ArrowUpDown } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Exam } from "@/lib/store/calendarStore";

const columnHelper = createColumnHelper<Exam>();

/**
 * Cell Components - Extracted for performance
 * These are reusable components
 */
const CourseCell = ({
  courseCode,
  section,
}: {
  courseCode: string;
  section: string;
}) => (
  <div>
    <div className="font-medium">{courseCode}</div>
    <div className="text-xs text-muted-foreground">Section {section}</div>
  </div>
);

const ConflictCell = ({ conflicts }: { conflicts: number }) => (
  <div className="flex justify-center">
    {conflicts > 0 ? (
      <Badge variant="destructive" className="gap-1">
        <AlertCircle className="size-3" />
        {conflicts}
      </Badge>
    ) : (
      <span className="text-muted-foreground text-sm">—</span>
    )}
  </div>
);

const SortableHeader = ({
  label,
  column,
}: {
  label: string;
  column: Column<Exam, unknown>;
}) => (
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

/**
 * Creates column definitions for the exam table
 */

// biome-ignore lint/suspicious/noExplicitAny: cannot support string and number
export function createExamColumns(): ColumnDef<Exam, any>[] {
  return [
    columnHelper.accessor("courseCode", {
      id: "courseCode",
      header: ({ column }) => <SortableHeader label="Course" column={column} />,
      cell: (info) => (
        <CourseCell
          courseCode={info.getValue()}
          section={info.row.original.section}
        />
      ),
      filterFn: (row, id, value) => {
        const cellValue = row.getValue(id) as string;
        return cellValue.toLowerCase().includes(value.toLowerCase());
      },
    }),
    columnHelper.accessor("day", {
      id: "day",
      header: ({ column }) => <SortableHeader label="Day" column={column} />,
      cell: (info) => <div className="text-sm">{info.getValue()}</div>,
    }),
    columnHelper.accessor("timeSlot", {
      id: "timeSlot",
      header: ({ column }) => <SortableHeader label="Time" column={column} />,
      cell: (info) => <div className="text-sm">{info.getValue()}</div>,
    }),
    columnHelper.accessor("room", {
      id: "room",
      header: ({ column }) => <SortableHeader label="Room" column={column} />,
      cell: (info) => (
        <div className="text-sm font-mono">{info.getValue()}</div>
      ),
    }),
    columnHelper.accessor("instructor", {
      id: "instructor",
      header: ({ column }) => (
        <SortableHeader label="Instructor" column={column} />
      ),
      cell: (info) => (
        <div className="text-sm max-w-[200px] truncate" title={info.getValue()}>
          {info.getValue()}
        </div>
      ),
    }),
    columnHelper.accessor("studentCount", {
      id: "studentCount",
      header: ({ column }) => (
        <div className="text-right">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
            className="-mr-3"
          >
            Students
            <ArrowUpDown className="ml-2 size-4" />
          </Button>
        </div>
      ),
      cell: (info) => (
        <div className="text-sm text-right font-medium">{info.getValue()}</div>
      ),
    }),
    columnHelper.accessor("conflicts", {
      id: "conflicts",
      header: ({ column }) => (
        <div className="text-center">
          <SortableHeader label="Conflicts" column={column} />
        </div>
      ),
      cell: (info) => <ConflictCell conflicts={info.getValue()} />,
    }),
  ];
}
