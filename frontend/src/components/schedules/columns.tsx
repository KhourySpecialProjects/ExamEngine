import { type ColumnDef, createColumnHelper } from "@tanstack/react-table";
import { Eye, MoreHorizontal, Trash2 } from "lucide-react";
import Link from "next/link";
import { SortableHeader } from "@/components/common/table/SortableHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { ScheduleListItem } from "@/lib/api/schedules";

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

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

export function createScheduleColumns(
  onDelete?: (scheduleId: string) => void,
): ColumnDef<ScheduleListItem, any>[] {
  return [
    columnHelper.accessor("schedule_name", {
      id: "schedule_name",
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
      header: ({ column }) => (
        <SortableHeader column={column} label="Created" />
      ),
      cell: (info) => formatDate(info.getValue()),
    }),

    columnHelper.accessor("total_exams", {
      id: "total_exams",
      header: ({ column }) => (
        <SortableHeader column={column} label="Total Exams" />
      ),
      cell: (info) => (
        <span className="font-medium">{info.getValue().toLocaleString()}</span>
      ),
    }),

    columnHelper.accessor("algorithm", {
      id: "algorithm",
      header: "Algorithm",
      cell: (info) => (
        <Badge variant="outline" className="font-mono">
          {info.getValue()}
        </Badge>
      ),
    }),

    columnHelper.accessor("status", {
      id: "status",
      header: "Status",
      cell: (info) => (
        <Badge variant={getStatusVariant(info.getValue())}>
          {info.getValue()}
        </Badge>
      ),
    }),

    columnHelper.display({
      id: "parameters",
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
}
