"use client";

import * as React from "react";
import type { CSSProperties, ReactNode } from "react";
import {
  Legend as RechartsLegend,
  type LegendProps,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  type TooltipProps,
} from "recharts";

import { cn } from "@/lib/utils";

export type ChartConfig = Record<
  string,
  {
    /**
     * Human-friendly label for the data series.
     */
    label?: string;
    /**
     * Tailwind/OKLCH/HEX/etc color value used to set a CSS variable.
     * Example: "hsl(var(--chart-1))"
     */
    color?: string;
    /**
     * Optional icon component rendered next to the legend label.
     */
    icon?: React.ComponentType<{ className?: string }>;
  }
>;

type ChartContainerProps = React.HTMLAttributes<HTMLDivElement> & {
  /**
   * Configuration describing each data series rendered inside the chart.
   * Each key becomes available as CSS variable: `--color-${key}`.
   */
  config: ChartConfig;
  children: ReactNode;
};

const ChartContext = React.createContext<ChartConfig | null>(null);

function useChartConfig() {
  const context = React.useContext(ChartContext);
  if (!context) {
    throw new Error("useChartConfig must be used within a <ChartContainer />");
  }
  return context;
}

function chartColorFallback(index: number) {
  const cycle = (index % 5) + 1;
  return `hsl(var(--chart-${cycle}))`;
}

export function ChartContainer({
  className,
  style,
  config,
  children,
  ...props
}: ChartContainerProps) {
  const cssVariables = React.useMemo(() => {
    const entries = Object.entries(config);
    const variables: CSSProperties = {};
    entries.forEach(([key, value], index) => {
      const sanitizedKey = key.replace(/\s+/g, "-").toLowerCase();
      variables[`--color-${sanitizedKey}` as keyof CSSProperties] =
        value?.color ?? chartColorFallback(index);
    });
    return variables;
  }, [config]);

  return (
    <ChartContext.Provider value={config}>
      <div
        className={cn("relative flex min-h-[200px] w-full", className)}
        style={{ ...cssVariables, ...style }}
        {...props}
      >
        <ResponsiveContainer>{children}</ResponsiveContainer>
      </div>
    </ChartContext.Provider>
  );
}

type ChartTooltipProps<
  TValue extends number | string,
  TName extends number | string,
> = TooltipProps<TValue, TName> & {
  /**
   * Optional props forwarded to the tooltip content renderer.
   */
  contentProps?: ChartTooltipContentProps;
};

export function ChartTooltip<
  TValue extends number | string,
  TName extends number | string,
>({
  contentProps,
  ...props
}: ChartTooltipProps<TValue, TName>) {
  return (
    <RechartsTooltip
      cursor={{ fill: "hsl(var(--muted))", opacity: 0.3 }}
      {...props}
      content={<ChartTooltipContent {...contentProps} />}
    />
  );
}

export type ChartTooltipContentProps = {
  className?: string;
  indicator?: "dot" | "line";
};

export function ChartTooltipContent<
  TValue extends number | string,
  TName extends number | string,
>({
  active,
  payload,
  label,
  className,
  indicator = "dot",
}: TooltipProps<TValue, TName> & ChartTooltipContentProps) {
  if (!active || !payload?.length) {
    return null;
  }

  const config = React.useContext(ChartContext);

  return (
    <div
      className={cn(
        "grid gap-2 rounded-md border bg-background p-2 text-xs shadow-md",
        className,
      )}
    >
      {label != null && (
        <div className="font-medium text-foreground">{label}</div>
      )}
      <div className="grid gap-1">
        {payload.map((item, index) => {
          const key =
            (typeof item.dataKey === "string" && item.dataKey) ||
            (typeof item.name === "string" && item.name) ||
            `item-${index}`;

          const sanitizedKey = key.replace(/\s+/g, "-").toLowerCase();
          const configEntry = config?.[key];
          const displayLabel =
            configEntry?.label ??
            (typeof item.name === "string"
              ? item.name
              : item.payload && typeof item.payload === "object"
                ? (item.payload as Record<string, unknown>).name ??
                  key.toString()
                : key.toString());

          const color =
            item.color ||
            (configEntry?.color ?? `var(--color-${sanitizedKey})`);

          return (
            <div
              key={`${key}-${index}`}
              className="flex items-center justify-between gap-2"
            >
              <div className="flex items-center gap-2">
                <span
                  className={cn(
                    "inline-flex h-2 w-2",
                    indicator === "dot" && "rounded-full",
                    indicator === "line" && "h-0.5",
                  )}
                  style={{ backgroundColor: color }}
                />
                <span className="text-muted-foreground">{displayLabel}</span>
              </div>
              <span className="font-medium text-foreground">
                {typeof item.value === "number"
                  ? item.value.toLocaleString()
                  : item.value}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

type ChartLegendProps = LegendProps & {
  contentProps?: ChartLegendContentProps;
};

export function ChartLegend({ contentProps, ...props }: ChartLegendProps) {
  return (
    <RechartsLegend
      {...props}
      content={<ChartLegendContent {...contentProps} />}
    />
  );
}

export type ChartLegendContentProps = {
  className?: string;
  hideIcon?: boolean;
};

type ChartLegendContentComponentProps = LegendProps & ChartLegendContentProps;

export function ChartLegendContent({
  className,
  hideIcon = false,
  payload,
}: ChartLegendContentComponentProps) {
  const config = useChartConfig();
  if (!payload?.length) {
    return null;
  }

  return (
    <div className={cn("flex flex-wrap items-center gap-3 text-sm", className)}>
      {payload.map((entry, index) => {
        const key =
          (typeof entry.value === "string" && entry.value) ||
          (typeof entry.id === "string" && entry.id) ||
          `item-${index}`;
        const sanitizedKey = key.replace(/\s+/g, "-").toLowerCase();
        const configEntry = config[key];
        const color =
          entry.color || configEntry?.color || `var(--color-${sanitizedKey})`;

        return (
          <div
            key={`${key}-${index}`}
            className="flex items-center gap-2 text-muted-foreground"
          >
            {!hideIcon && (
              <span
                className="inline-flex h-2 w-2 rounded-full"
                style={{ backgroundColor: color }}
              />
            )}
            <span className="font-medium text-foreground">
              {configEntry?.label ?? key}
            </span>
            {configEntry?.icon && <configEntry.icon className="h-3 w-3" />}
          </div>
        );
      })}
    </div>
  );
}

