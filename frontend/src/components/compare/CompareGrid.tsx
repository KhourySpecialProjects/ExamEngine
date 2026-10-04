import { Info } from "lucide-react";
import { createContext, type ReactNode, useContext } from "react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import type { ComparedSchedule } from "@/lib/api/schedules";
import type { COLUMN_COLORS } from "@/lib/compare";
import { cn } from "@/lib/utils";

/** A column of the Compare page; `schedule` is set when it can be shown. */
export interface GridColumn {
  id: string;
  letter: string;
  color: (typeof COLUMN_COLORS)[number];
  schedule: ComparedSchedule | null;
  isBaseline: boolean;
}

export type ShownColumn = GridColumn & { schedule: ComparedSchedule };

const ColumnsContext = createContext<GridColumn[]>([]);

export function useGridColumns(): GridColumn[] {
  return useContext(ColumnsContext);
}

export function shownColumns(columns: GridColumn[]): ShownColumn[] {
  return columns.filter((c): c is ShownColumn => c.schedule !== null);
}

/**
 * Wide container (≥ 56rem, i.e. 4 columns at 1280 px with the sidebar open):
 * a narrow label column, then one column per schedule. Narrower: each metric
 * becomes a card listing the schedules one under another. Neither scrolls
 * sideways.
 */
export const WIDE_ROW =
  "@4xl:grid @4xl:gap-x-4 @4xl:grid-cols-[minmax(7rem,10rem)_repeat(var(--compare-cols),minmax(0,1fr))]";

export function CompareGrid({
  columns,
  children,
}: {
  columns: GridColumn[];
  children: ReactNode;
}) {
  return (
    <ColumnsContext.Provider value={columns}>
      <div
        className="@container"
        style={{ "--compare-cols": columns.length } as React.CSSProperties}
      >
        {children}
      </div>
    </ColumnsContext.Provider>
  );
}

/** The column's letter in its colour. */
export function ColumnBadge({
  column,
  className,
}: {
  column: Pick<GridColumn, "letter" | "color">;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold",
        className,
      )}
      style={{ backgroundColor: column.color.fill, color: column.color.text }}
    >
      {column.letter}
    </span>
  );
}

export function InfoPopover({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <Popover>
      <PopoverTrigger
        className="inline-flex shrink-0 rounded-full text-muted-foreground hover:text-foreground"
        aria-label={`About ${label}`}
      >
        <Info className="h-3.5 w-3.5" />
      </PopoverTrigger>
      <PopoverContent className="w-72 text-sm">{children}</PopoverContent>
    </Popover>
  );
}

/** A heading spanning the full width, then its metric rows. */
export function CompareSection({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  const id = `compare-${title.toLowerCase().replace(/\W+/g, "-")}`;
  return (
    <section aria-labelledby={id} className="space-y-2 @4xl:space-y-0">
      <h2
        id={id}
        className="pt-4 text-lg font-semibold @4xl:border-b @4xl:pb-2"
      >
        {title}
      </h2>
      {children}
    </section>
  );
}

/**
 * One metric: its label, then one cell per column. Columns that can't be
 * shown get an empty cell in the wide layout and are left out of the card.
 */
export function MetricRow({
  label,
  hint,
  info,
  cell,
}: {
  label: ReactNode;
  /** Small text under the label (e.g. a shared chart scale). */
  hint?: ReactNode;
  info?: ReactNode;
  cell: (column: ShownColumn) => ReactNode;
}) {
  const columns = useGridColumns();
  const labelText = typeof label === "string" ? label : "this metric";
  return (
    <div
      className={cn(
        "rounded-lg border bg-card p-3",
        "@4xl:rounded-none @4xl:border-0 @4xl:border-b @4xl:bg-transparent @4xl:px-0 @4xl:py-3",
        WIDE_ROW,
      )}
    >
      <div className="min-w-0 text-sm">
        <div className="flex items-center gap-1.5 font-medium @4xl:text-muted-foreground">
          {label}
          {info && <InfoPopover label={labelText}>{info}</InfoPopover>}
        </div>
        {hint && <div className="text-xs text-muted-foreground">{hint}</div>}
      </div>
      <div className="mt-2 space-y-2 @4xl:contents">
        {columns.map((column) =>
          column.schedule ? (
            <div
              key={column.id}
              className="flex min-w-0 items-start gap-2 @4xl:block"
            >
              <ColumnBadge column={column} className="mt-0.5 @4xl:hidden" />
              <div className="min-w-0 flex-1">
                {cell(column as ShownColumn)}
              </div>
            </div>
          ) : (
            <div key={column.id} className="hidden @4xl:block" aria-hidden />
          ),
        )}
      </div>
    </div>
  );
}
