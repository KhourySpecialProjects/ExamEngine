import { calendarShape } from "@/lib/compare";
import { Heatmap, MiniBarChart } from "./CompareCharts";
import {
  CompareSection,
  MetricRow,
  shownColumns,
  useGridColumns,
} from "./CompareGrid";

/** Placed exams per day and block, all columns on one scale per chart. */
export function CalendarShapeSection() {
  const columns = shownColumns(useGridColumns());
  const shape = calendarShape(columns.map((c) => c.schedule.summary));
  const shapeOf = (id: string) =>
    shape.schedules[columns.findIndex((c) => c.id === id)];
  // Axis label: the start ("11:30AM"); hover: the whole block ("11:30AM-1:30PM").
  const blocks = shape.blocks.map((block) => ({
    label: block.split("-")[0].trim(),
    title: block,
  }));

  return (
    <CompareSection title="Calendar shape">
      <MetricRow
        label="Days used"
        cell={(column) => (
          <span className="text-sm font-semibold tabular-nums">
            {column.schedule.summary.calendar.days_used}
          </span>
        )}
      />
      <MetricRow
        label="Time slots used"
        info="Distinct (day, block) pairs holding an exam."
        cell={(column) => (
          <span className="text-sm font-semibold tabular-nums">
            {column.schedule.summary.calendar.slots_used}
          </span>
        )}
      />
      <MetricRow
        label="Exams per day"
        hint={`Same scale (max ${shape.maxDay})`}
        cell={(column) => (
          <MiniBarChart
            data={shape.days.map((day, i) => ({
              label: day.slice(0, 3),
              title: day,
              value: shapeOf(column.id).days[i],
            }))}
            max={shape.maxDay}
            color={column.color.fill}
          />
        )}
      />
      <MetricRow
        label="Exams per block"
        hint={`Same scale (max ${shape.maxBlock})`}
        cell={(column) => (
          <MiniBarChart
            data={blocks.map((block, i) => ({
              ...block,
              value: shapeOf(column.id).blocks[i],
            }))}
            max={shape.maxBlock}
            color={column.color.fill}
          />
        )}
      />
      <MetricRow
        label="Day × block"
        hint={`Exams in each slot; same shading scale (max ${shape.maxCell})`}
        cell={(column) => (
          <Heatmap
            days={shape.days}
            blocks={blocks}
            matrix={shapeOf(column.id).matrix}
            max={shape.maxCell}
            color={column.color}
          />
        )}
      />
    </CompareSection>
  );
}
