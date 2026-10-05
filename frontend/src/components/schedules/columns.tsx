import { type ColumnDef, createColumnHelper } from "@tanstack/react-table";
import { Eye, MoreHorizontal, Trash2 } from "lucide-react";
import Link from "next/link";
import { SortableHeader } from "@/components/common/table/SortableHeader";
import { LateAddBadge } from "@/components/schedule/LateAddBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { LATE_ADD_ALGORITHM, type ScheduleListItem } from "@/lib/api/schedules";
import { cn } from "@/lib/utils";

const columnHelper = createColumnHelper<ScheduleListItem>();

function getStatusVariant(
  status: string,
): "default" | "secondary" | "destructive" {
  switch (status) {
    case "Completed":
      return "default";
    case "Running":
      return "secondary";
    case "Failed":
      return "destructive";
    default:
      return "default";
  }
}

const dateFormat = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
});
const timeFormat = new Intl.DateTimeFormat("en-US", {
  hour: "numeric",
  minute: "2-digit",
});

export function createScheduleColumns(
  onDelete?: (scheduleId: string) => void,
  /** The By-dataset view shows the dataset in the group header instead. */
  { showDataset = true }: { showDataset?: boolean } = {},
  // biome-ignore lint/suspicious/noExplicitAny: table types needs to be flexible
): ColumnDef<ScheduleListItem, any>[] {
  const columns = [
    // Picks schedules for Compare. No select-all: Compare takes a few.
    columnHelper.display({
      id: "select",
      meta: { width: "w-[4%]" },
      enableHiding: false,
      header: () => <span className="sr-only">Select to compare</span>,
      cell: ({ row, table }) => {
        const blocker = table.options.meta?.selectionBlocker?.(row.original);
        // A disabled button gets no hover in some browsers: the wrapper shows
        // the reason instead.
        return (
          <span
            title={blocker ?? undefined}
            className={cn("flex", blocker && "cursor-not-allowed")}
          >
            <Checkbox
              aria-label={`Select ${row.original.schedule_name}`}
              checked={row.getIsSelected()}
              disabled={!row.getCanSelect()}
              onCheckedChange={(checked) =>
                row.toggleSelected(checked === true)
              }
              className="disabled:pointer-events-none"
            />
          </span>
        );
      },
    }),

    columnHelper.accessor("schedule_name", {
      id: "schedule_name",
      meta: { width: "w-[14%]" },
      header: ({ column }) => (
        <SortableHeader column={column} label="Schedule Name" />
      ),
      cell: (info) => (
        <Link
          href={`/dashboard/${info.row.original.schedule_id}`}
          className="font-medium hover:underline"
        >
          {info.getValue()}
        </Link>
      ),
    }),

    columnHelper.accessor("created_at", {
      id: "created_at",
      meta: { width: "w-[10%]" },
      header: ({ column }) => (
        <SortableHeader column={column} label="Created" />
      ),
      cell: (info) => {
        const date = new Date(info.getValue());
        return (
          <div className="flex flex-col">
            <span>{dateFormat.format(date)}</span>
            <span className="text-xs text-muted-foreground">
              {timeFormat.format(date)}
            </span>
          </div>
        );
      },
    }),

    columnHelper.accessor((row) => row.dataset.name, {
      id: "dataset",
      meta: { width: "w-[13%]" },
      header: ({ column }) => (
        <SortableHeader column={column} label="Dataset" />
      ),
      cell: (info) => (
        <div className="flex flex-wrap items-center gap-2">
          <span>{info.getValue() || "Unknown"}</span>
          {info.row.original.dataset.deleted && (
            <Badge variant="destructive">Deleted</Badge>
          )}
        </div>
      ),
    }),

    columnHelper.display({
      id: "created_by",
      meta: { width: "w-[11%]" },
      header: "Created by",
      cell: (info) => {
        const schedule = info.row.original;
        if (schedule.is_shared && schedule.shared_by_user_name) {
          return (
            <div className="flex flex-col">
              <span className="text-sm font-medium">
                Shared by {schedule.shared_by_user_name}
              </span>
              <span className="text-xs text-muted-foreground">
                Created by {schedule.created_by_user_name || "Unknown"}
              </span>
            </div>
          );
        }
        return (
          <span className="text-sm">
            {schedule.created_by_user_name || "Unknown"}
          </span>
        );
      },
    }),

    columnHelper.accessor("total_exams", {
      id: "total_exams",
      meta: { width: "w-[11%]" },
      header: ({ column }) => (
        <SortableHeader column={column} label="Total Exams" />
      ),
      cell: (info) => (
        <span className="font-medium">{info.getValue().toLocaleString()}</span>
      ),
    }),

    columnHelper.accessor("algorithm", {
      id: "algorithm",
      meta: { width: "w-[11%]" },
      header: ({ column }) => (
        <SortableHeader column={column} label="Algorithm" />
      ),
      cell: (info) => {
        const { algorithm, late_add_count, based_on_name } = info.row.original;
        if (algorithm === LATE_ADD_ALGORITHM || late_add_count > 0) {
          return (
            <LateAddBadge
              title={
                based_on_name
                  ? `Based on ${based_on_name}`
                  : "Based on a schedule that is not available"
              }
            />
          );
        }
        return (
          <Badge variant="outline" className="font-mono">
            {algorithm}
          </Badge>
        );
      },
    }),

    columnHelper.accessor("status", {
      id: "status",
      meta: { width: "w-[9%]" },
      header: ({ column }) => <SortableHeader column={column} label="Status" />,
      cell: (info) => (
        <Badge variant={getStatusVariant(info.getValue())}>
          {info.getValue()}
        </Badge>
      ),
    }),

    columnHelper.display({
      id: "parameters",
      meta: { width: "w-[10%]" },
      header: "Parameters",
      cell: (info) => {
        const params = info.row.original.parameters;
        return (
          <div className="text-sm text-muted-foreground">
            <div>Max/day: {params.student_max_per_day || "N/A"}</div>
            <div>
              B2B:{" "}
              {params.avoid_back_to_back !== undefined
                ? params.avoid_back_to_back
                  ? "Avoid"
                  : "Allow"
                : "N/A"}
            </div>
          </div>
        );
      },
    }),

    columnHelper.display({
      id: "actions",
      meta: { width: "w-[7%]" },
      header: "Actions",
      cell: (info) => {
        const schedule = info.row.original;
        return (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                <span className="sr-only">Open menu</span>
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Actions</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem asChild>
                <Link
                  href={`/dashboard/${schedule.schedule_id}`}
                  className="flex items-center cursor-pointer"
                >
                  <Eye className="mr-2 h-4 w-4" />
                  View Schedule
                </Link>
              </DropdownMenuItem>
              {onDelete && (
                <DropdownMenuItem
                  onClick={() => onDelete(schedule.schedule_id)}
                  variant="destructive"
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete
                </DropdownMenuItem>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        );
      },
    }),
  ];
  return showDataset ? columns : columns.filter((c) => c.id !== "dataset");
}
