import { type ColumnDef, createColumnHelper } from "@tanstack/react-table";
import { AlertCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { SortableHeader } from "@/components/common/table/SortableHeader";
import type { Exam } from "@/lib/store/calendarStore";

const columnHelper = createColumnHelper<Exam>();

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

export function createExamColumns(): ColumnDef<Exam, any>[] {
  return [
    columnHelper.accessor("courseCode", {
      id: "courseCode",
      header: ({ column }) => <SortableHeader column={column} label="Course" />,
      cell: (info) => (
        <CourseCell
          courseCode={info.getValue()}
          section={info.row.original.section}
        />
      ),
    }),
    columnHelper.accessor("day", {
      id: "day",
      header: ({ column }) => <SortableHeader column={column} label="Day" />,
      cell: (info) => <div className="text-sm">{info.getValue()}</div>,
    }),
    columnHelper.accessor("timeSlot", {
      id: "timeSlot",
      header: ({ column }) => <SortableHeader column={column} label="Time" />,
      cell: (info) => <div className="text-sm">{info.getValue()}</div>,
    }),
    columnHelper.accessor("room", {
      id: "room",
      header: ({ column }) => <SortableHeader column={column} label="Room" />,
      cell: (info) => (
        <div className="text-sm font-mono">{info.getValue()}</div>
      ),
    }),
    columnHelper.accessor("instructor", {
      id: "instructor",
      header: ({ column }) => (
        <SortableHeader column={column} label="Instructor" />
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
        <SortableHeader column={column} label="Students" />
      ),
      cell: (info) => (
        <div className="text-sm text-right font-medium">{info.getValue()}</div>
      ),
    }),
    columnHelper.accessor("conflicts", {
      id: "conflicts",
      header: ({ column }) => (
        <SortableHeader column={column} label="Conflicts" />
      ),
      cell: (info) => <ConflictCell conflicts={info.getValue()} />,
    }),
  ];
}
