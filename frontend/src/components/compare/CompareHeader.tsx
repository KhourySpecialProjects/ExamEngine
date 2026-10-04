import {
  type Announcements,
  closestCenter,
  DndContext,
  type DragEndEvent,
  KeyboardSensor,
  PointerSensor,
  type UniqueIdentifier,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  rectSortingStrategy,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import {
  ArrowLeft,
  ArrowRight,
  ExternalLink,
  Flag,
  GripVertical,
  MoreHorizontal,
  Trash2,
} from "lucide-react";
import Link from "next/link";
import type { CSSProperties, ReactNode } from "react";
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
  /** `id` takes the place of `target` (drag and drop). */
  reorder: (id: string, target: string) => void;
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
        {!column.isBaseline && (
          <>
            <DropdownMenuItem
              disabled={index <= 1}
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
          </>
        )}
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
  sortable,
}: {
  column: GridColumn;
  index: number;
  count: number;
  actions: ColumnActions;
  /** Set on the columns that can be dragged (all but the baseline). */
  sortable?: {
    ref: (node: HTMLElement | null) => void;
    style: CSSProperties;
    handle: ReactNode;
    dragging: boolean;
  };
}) {
  const schedule = column.schedule;
  return (
    <div
      ref={sortable?.ref}
      className={cn(
        "min-w-0 rounded-lg border-t-4 bg-card p-3 shadow-sm",
        sortable?.dragging && "relative z-20 shadow-lg",
      )}
      style={{ borderTopColor: column.color.fill, ...sortable?.style }}
      data-testid={`compare-column-${column.letter}`}
    >
      <div className="flex items-center gap-2">
        {sortable?.handle}
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

function SortableColumnHeader(props: {
  column: GridColumn;
  index: number;
  count: number;
  actions: ColumnActions;
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    setActivatorNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: props.column.id });
  return (
    <ColumnHeader
      {...props}
      sortable={{
        ref: setNodeRef,
        style: { transform: CSS.Translate.toString(transform), transition },
        dragging: isDragging,
        handle: (
          <button
            ref={setActivatorNodeRef}
            type="button"
            className="-ml-1 shrink-0 cursor-grab touch-none rounded p-0.5 text-muted-foreground hover:bg-accent active:cursor-grabbing"
            {...attributes}
            {...listeners}
            aria-label={`Drag column ${props.column.letter} to reorder`}
          >
            <GripVertical className="h-4 w-4" aria-hidden />
          </button>
        ),
      }}
    />
  );
}

/** Screen reader messages naming the columns, not their ids. */
function announcements(columns: GridColumn[]): Announcements {
  const name = (id: UniqueIdentifier) => {
    const column = columns.find((c) => c.id === id);
    if (!column) return "column";
    return `column ${column.letter}, ${column.schedule?.schedule_name ?? "not available"}`;
  };
  return {
    onDragStart: ({ active }) => `Picked up ${name(active.id)}.`,
    onDragOver: ({ active, over }) =>
      over
        ? `${name(active.id)} is over the place of ${name(over.id)}.`
        : `${name(active.id)} is not over a column.`,
    onDragEnd: ({ active, over }) =>
      over
        ? `${name(active.id)} was dropped in the place of ${name(over.id)}.`
        : `${name(active.id)} was dropped.`,
    onDragCancel: ({ active }) =>
      `Dragging was cancelled. ${name(active.id)} was dropped.`,
  };
}

/**
 * One card per column. Wide layout: aligned over the metric columns and
 * sticky while the page scrolls. Narrow: a plain list of the schedules.
 * Every column but the baseline (always first) can be dragged by its grip.
 */
export function CompareHeader({ actions }: { actions: ColumnActions }) {
  const columns = useGridColumns();
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );
  const [baseline, ...others] = columns;

  const onDragEnd = ({ active, over }: DragEndEvent) => {
    if (over && active.id !== over.id) {
      actions.reorder(String(active.id), String(over.id));
    }
  };

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragEnd={onDragEnd}
      accessibility={{ announcements: announcements(columns) }}
    >
      <div
        className={cn(
          "grid gap-2 sm:grid-cols-2",
          "@4xl:sticky @4xl:top-0 @4xl:z-10 @4xl:bg-gray-50/95 @4xl:py-2 @4xl:backdrop-blur",
          WIDE_ROW,
        )}
      >
        <div className="hidden @4xl:block" />
        {baseline && (
          <ColumnHeader
            column={baseline}
            index={0}
            count={columns.length}
            actions={actions}
          />
        )}
        <SortableContext
          items={others.map((c) => c.id)}
          strategy={rectSortingStrategy}
        >
          {others.map((column, i) => (
            <SortableColumnHeader
              key={column.id}
              column={column}
              index={i + 1}
              count={columns.length}
              actions={actions}
            />
          ))}
        </SortableContext>
      </div>
    </DndContext>
  );
}
