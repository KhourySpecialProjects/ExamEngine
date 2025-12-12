import { type ColumnDef, createColumnHelper } from "@tanstack/react-table";
import { AlertCircle, GitMerge } from "lucide-react";
import { SortableHeader } from "@/components/common/table/SortableHeader";
import { Badge } from "@/components/ui/badge";
import type { Exam } from "@/lib/types/calendar.types";

const columnHelper = createColumnHelper<Exam>();

const CourseCell = ({
  courseCode,
  section,
  isMerged = false,
}: {
  courseCode: string;
  section: string;
  isMerged?: boolean;
}) => (
  <div>
    <div className="flex items-center gap-2">
      <span className="font-medium">{courseCode}</span>
      {isMerged && (
        <Badge variant="outline" className="gap-1 text-xs px-1.5 py-0.5 border-blue-300 text-blue-700 bg-blue-50/50 flex items-center" title="Merged course">
          <GitMerge className="h-3 w-3" />
        </Badge>
      )}
    </div>
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

export function createExamColumns(
  isMerged?: (crn: string) => boolean,
): ColumnDef<Exam, any>[] {
  return [
    columnHelper.accessor("courseCode", {
      id: "courseCode",
      header: ({ column }) => <SortableHeader column={column} label="Course" />,
      cell: (info) => (
        <CourseCell
          courseCode={info.getValue()}
          section={info.row.original.section}
          isMerged={isMerged ? isMerged(info.row.original.section) : false}
        />
      ),
    }),
    columnHelper.accessor("day", {
      id: "day",
      header: ({ column }) => <SortableHeader column={column} label="Day" />,
      cell: (info) => (
        <div className="text-sm">
          {info.row.original.isUnscheduled ? (
            <span className="text-muted-foreground italic">Unscheduled</span>
          ) : (
            info.getValue()
          )}
        </div>
      ),
    }),
    columnHelper.accessor("timeSlot", {
      id: "timeSlot",
      header: ({ column }) => <SortableHeader column={column} label="Time" />,
      cell: (info) => (
        <div className="text-sm">
          {info.row.original.isUnscheduled ? (
            <span className="text-muted-foreground">—</span>
          ) : (
            info.getValue()
          )}
        </div>
      ),
    }),
    columnHelper.accessor("room", {
      id: "room",
      header: ({ column }) => <SortableHeader column={column} label="Room" />,
      cell: (info) => (
        <div className="text-sm font-mono">
          {info.row.original.isUnscheduled ? (
            <span className="text-muted-foreground">—</span>
          ) : (
            info.getValue()
          )}
        </div>
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
        <div className="text-sm font-medium">{info.getValue()}</div>
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
