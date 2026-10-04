import { type MouseEvent, useState } from "react";
import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  type TooltipProps,
  XAxis,
  YAxis,
} from "recharts";
import { cn } from "@/lib/utils";

/** Charts of the Compare page: same size, axis text and hover panel. */

const CHART_HEIGHT = "h-24";
const AXIS_TEXT = { fontSize: 10, fill: "var(--muted-foreground)" };

const exams = (n: number) => `${n.toLocaleString()} exam${n === 1 ? "" : "s"}`;

/** The hover panel every compare chart shows. */
function ChartTooltip({
  title,
  value,
  color,
}: {
  title: string;
  value: number;
  color: string;
}) {
  return (
    <div className="pointer-events-none w-max whitespace-nowrap rounded-md border bg-popover px-2.5 py-1.5 text-xs text-popover-foreground shadow-md">
      <div className="font-medium">{title}</div>
      <div className="mt-0.5 flex items-center gap-1.5 tabular-nums text-muted-foreground">
        <span
          className="h-2 w-2 shrink-0 rounded-full"
          style={{ backgroundColor: color }}
        />
        {exams(value)}
      </div>
    </div>
  );
}

export interface BarDatum {
  /** Axis label ("Mon"). */
  label: string;
  /** Hover title ("Monday"). */
  title: string;
  value: number;
}

/** A small bar chart on a fixed y scale, so columns compare at a glance. */
export function MiniBarChart({
  data,
  max,
  color,
}: {
  data: BarDatum[];
  max: number;
  color: string;
}) {
  const content = ({ active, payload }: TooltipProps<number, string>) => {
    const datum = payload?.[0]?.payload as BarDatum | undefined;
    return active && datum ? (
      <ChartTooltip title={datum.title} value={datum.value} color={color} />
    ) : null;
  };
  return (
    <div className={cn(CHART_HEIGHT, "w-full")}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
          <XAxis
            dataKey="label"
            interval={0}
            tickLine={false}
            axisLine={false}
            tick={AXIS_TEXT}
            height={16}
          />
          <YAxis hide domain={[0, Math.max(max, 1)]} />
          <Tooltip
            content={content}
            cursor={{ fill: "rgba(0,0,0,0.04)" }}
            isAnimationActive={false}
            wrapperStyle={{ outline: "none" }}
          />
          <Bar
            dataKey="value"
            fill={color}
            radius={[2, 2, 0, 0]}
            isAnimationActive={false}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

interface Hover {
  day: number;
  block: number;
  x: number;
  y: number;
  /** Cursor in the right half: the panel opens to its left. */
  flip: boolean;
}

/**
 * Exams per day × block in the column's colour, with the count in each cell.
 * One shade scale (`max`) across all columns, so the same count is the same
 * shade everywhere. Taller than the bar charts: up to 7 rows of numbers.
 */
export function Heatmap({
  days,
  blocks,
  matrix,
  max,
  color,
}: {
  days: string[];
  blocks: { label: string; title: string }[];
  matrix: number[][];
  max: number;
  /** The column's colour and the text colour readable on it. */
  color: { fill: string; text: string };
}) {
  const [hover, setHover] = useState<Hover | null>(null);
  const track = (day: number, block: number) => (e: MouseEvent) => {
    const box = e.currentTarget
      .closest("[data-heatmap]")
      ?.getBoundingClientRect();
    if (!box) return;
    const x = e.clientX - box.left;
    setHover({
      day,
      block,
      x,
      y: e.clientY - box.top,
      flip: x > box.width / 2,
    });
  };

  return (
    <div
      data-heatmap
      className="relative h-40 w-full"
      onMouseLeave={() => setHover(null)}
    >
      <div
        className="grid h-full gap-0.5 pt-1"
        style={{
          gridTemplateColumns: `1.75rem repeat(${blocks.length}, minmax(0, 1fr))`,
          gridTemplateRows: `repeat(${days.length}, minmax(0, 1fr)) 16px`,
        }}
      >
        {days.map((day, d) => [
          <div
            key={`${day}-label`}
            className="flex items-center text-[10px] leading-none text-muted-foreground"
          >
            {day.slice(0, 3)}
          </div>,
          ...blocks.map((block, b) => {
            const n = matrix[d][b];
            // Share of the column colour mixed into white: 15–100%.
            const strength = 15 + 85 * (n / Math.max(max, 1));
            const isHovered = hover?.day === d && hover.block === b;
            return (
              <div
                key={`${day}-${block.label}`}
                className={cn(
                  "flex items-center justify-center rounded-sm text-[11px] font-medium tabular-nums",
                  isHovered && "ring-1 ring-foreground/40",
                )}
                style={{
                  backgroundColor:
                    n === 0
                      ? "rgba(0,0,0,0.04)"
                      : `color-mix(in srgb, ${color.fill} ${strength}%, white)`,
                  // Dark cells take the text colour readable on the full fill.
                  color: strength > 60 ? color.text : "var(--foreground)",
                }}
                onMouseMove={track(d, b)}
              >
                {/* Empty cells stay blank; the hover still says 0. */}
                {n > 0 && <span aria-hidden>{n.toLocaleString()}</span>}
                <span className="sr-only">
                  {day} {block.title}: {exams(n)}
                </span>
              </div>
            );
          }),
        ])}
        <div />
        {blocks.map((block) => (
          <div
            key={block.label}
            className="truncate text-center text-[10px] leading-4 text-muted-foreground"
          >
            {block.label}
          </div>
        ))}
      </div>
      {hover && (
        <div
          className="absolute z-20"
          style={{
            left: hover.x,
            top: hover.y,
            transform: `translate(${hover.flip ? "calc(-100% - 10px)" : "10px"}, 10px)`,
          }}
        >
          <ChartTooltip
            title={`${days[hover.day]} · ${blocks[hover.block].title}`}
            value={matrix[hover.day][hover.block]}
            color={color.fill}
          />
        </div>
      )}
    </div>
  );
}
