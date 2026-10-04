import {
  ArrowLeft,
  ArrowRight,
  ExternalLink,
  Flag,
  MoreHorizontal,
  Trash2,
} from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { scheduleHref } from "@/lib/scheduleView";
import { cn } from "@/lib/utils";
import {
  ColumnBadge,
  type GridColumn,
  useGridColumns,
  WIDE_ROW,
} from "./CompareGrid";

export interface ColumnActions {
  setBaseline: (id: string) => void;
  move: (id: string, offset: -1 | 1) => void;
  remove: (id: string) => void;
}

function ColumnMenu({
  column,
  index,
  count,
  actions,
}: {
  column: GridColumn;
  index: number;
  count: number;
  actions: ColumnActions;
}) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon-sm"
          className="-mr-1 shrink-0"
          aria-label={`Column ${column.letter} options`}
        >
          <MoreHorizontal className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {column.schedule && (
          <DropdownMenuItem
            disabled={column.isBaseline}
            onSelect={() => actions.setBaseline(column.id)}
          >
            <Flag className="h-4 w-4" />
            Set as baseline
          </DropdownMenuItem>
        )}
        <DropdownMenuItem
          disabled={index === 0}
          onSelect={() => actions.move(column.id, -1)}
        >
          <ArrowLeft className="h-4 w-4" />
          Move left
        </DropdownMenuItem>
        <DropdownMenuItem
          disabled={index === count - 1}
          onSelect={() => actions.move(column.id, 1)}
        >
          <ArrowRight className="h-4 w-4" />
          Move right
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          variant="destructive"
          onSelect={() => actions.remove(column.id)}
        >
          <Trash2 className="h-4 w-4" />
          Remove
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function ColumnHeader({
  column,
  index,
  count,
  actions,
}: {
  column: GridColumn;
  index: number;
  count: number;
  actions: ColumnActions;
}) {
  const schedule = column.schedule;
  return (
    <div
      className="min-w-0 rounded-lg border-t-4 bg-card p-3 shadow-sm"
      style={{ borderTopColor: column.color.fill }}
      data-testid={`compare-column-${column.letter}`}
    >
      <div className="flex items-center gap-2">
        <ColumnBadge column={column} />
        {column.isBaseline && <Badge variant="secondary">Baseline</Badge>}
        {schedule && schedule.run_status !== "Completed" && (
          <Badge variant="outline">{schedule.run_status}</Badge>
        )}
        <div className="flex-1" />
        <ColumnMenu
          column={column}
          index={index}
          count={count}
          actions={actions}
        />
      </div>
      {schedule ? (
        <div className="mt-1 min-w-0">
          <div
            className="truncate font-semibold"
            title={schedule.schedule_name}
          >
            {schedule.schedule_name}
          </div>
          <div
            className="truncate text-xs text-muted-foreground"
            title={schedule.dataset.dataset_name}
          >
            {schedule.dataset.dataset_name}
            {schedule.dataset.deleted && " (deleted)"}
          </div>
          <Button variant="outline" size="sm" className="mt-2" asChild>
            <Link
              href={scheduleHref(schedule.schedule_id)}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={`View schedule ${schedule.schedule_name} (opens in a new tab)`}
            >
              View schedule
              <ExternalLink className="h-3.5 w-3.5" aria-hidden />
            </Link>
          </Button>
        </div>
      ) : (
        <div className="mt-1 space-y-2">
          <div className="font-semibold">Not available</div>
          <p className="text-xs text-muted-foreground">
            This schedule may have been deleted or not shared with you.
          </p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => actions.remove(column.id)}
          >
            Remove
          </Button>
        </div>
      )}
    </div>
  );
}

/**
 * One card per column. Wide layout: aligned over the metric columns and
 * sticky while the page scrolls. Narrow: a plain list of the schedules.
 */
export function CompareHeader({ actions }: { actions: ColumnActions }) {
  const columns = useGridColumns();
  return (
    <div
      className={cn(
        "grid gap-2 sm:grid-cols-2",
        "@4xl:sticky @4xl:top-0 @4xl:z-10 @4xl:bg-gray-50/95 @4xl:py-2 @4xl:backdrop-blur",
        WIDE_ROW,
      )}
    >
      <div className="hidden @4xl:block" />
      {columns.map((column, index) => (
        <ColumnHeader
          key={column.id}
          column={column}
          index={index}
          count={columns.length}
          actions={actions}
        />
      ))}
    </div>
  );
}
