import { useMemo } from "react";
import { EmptyScheduleState } from "@/components/common/EmptyScheduleState";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { colorThemes, THEME_KEYS } from "@/lib/constants/colorThemes";
import { useScheduleData } from "@/lib/hooks/useScheduleData";
import { useCalendarStore } from "@/lib/store/calendarStore";
import { getReadableTextColorFromBg } from "@/lib/utils";
import { CalendarGrid } from "./CalendarGrid";

const DAYS = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];
/**
 * Calculate dynamic thresholds based on data distribution (percentile)
 */
const calculateThresholds = (counts: number[]) => {
  const nonZero = counts.filter((c) => c > 0).sort((a, b) => a - b);
  if (nonZero.length === 0) return { t1: 0, t2: 0, t3: 0, t4: 0 };

  const len = nonZero.length;
  return {
    t1: nonZero[Math.floor(len * 0.25)] || nonZero[0],
    t2: nonZero[Math.floor(len * 0.5)] || nonZero[0],
    t3: nonZero[Math.floor(len * 0.75)] || nonZero[0],
    t4: nonZero[len - 1],
  };
};

/**
 * Get color based on thresholds
 */
const getDensityColor = (
  count: number,
  thresholds: ReturnType<typeof calculateThresholds>,
  themeColors: string[],
): { bg: string; color: string } => {
  // Map count to level 0..4 using thresholds
  let level = 0;
  if (count === 0) level = 0;
  else if (count <= thresholds.t1) level = 1;
  else if (count <= thresholds.t2) level = 2;
  else if (count <= thresholds.t3) level = 3;
  else level = 4;

  const bg = themeColors[level] || themeColors[0];

  // Determine readable text color (black or white) based on luminance
  const color = getReadableTextColorFromBg(bg);

  return { bg, color };
};

/**
 * DensityMapView - Heatmap visualization of exam schedule
 *
 * Shows exam count with color-coded density.
 * Click cell to open detail modal.
 */
export default function DensityView() {
  const { hasData, isLoading, calendarRows } = useScheduleData();
  const selectCell = useCalendarStore((state) => state.selectCell);
  const theme = useCalendarStore((s) => s.colorTheme || "gray");
  const setTheme = useCalendarStore((s) => s.setColorTheme);
  const thresholds = useMemo(() => {
    const counts = calendarRows.flatMap((row) =>
      row.days.map((d) => d.examCount),
    );
    return calculateThresholds(counts);
  }, [calendarRows]);

  if (!hasData) return <EmptyScheduleState isLoading={isLoading} />;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <div className="pl-2">
          <h1 className="text-2xl font-bold">Density View</h1>
          <p className="text-muted-foreground">
            Color-coded heat map of exam distribution and conflicts
          </p>
        </div>
        <Select value={theme} onValueChange={(val) => setTheme(val)}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Choose a Theme" />
          </SelectTrigger>
          <SelectContent>
            {THEME_KEYS.map((k) => (
              <SelectItem key={k} value={k}>
                Theme: {k.charAt(0).toUpperCase() + k.slice(1)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      {/* Calendar Grid */}
      <CalendarGrid
        data={calendarRows}
        days={DAYS}
        minCellHeight="h-[120px]"
        minCellWidth={140}
        defaultCellWidth={140}
        timeSlotWidth={140}
        renderCell={(cell) => {
          const examCount = cell ? cell.examCount : 0;
          const conflicts = cell ? cell.conflicts : 0;
          const themeColors = colorThemes[theme] || colorThemes.gray;
          const { bg, color } = getDensityColor(
            cell ? cell.examCount : 0,
            thresholds,
            themeColors,
          );

          return (
            <div
              onClick={() => examCount > 0 && cell && selectCell(cell)}
              style={{ backgroundColor: bg, color }}
              className={`w-full h-full flex items-center border border-gray-200 ${
                examCount > 0
                  ? "cursor-pointer hover:shadow-lg hover:z-10 relative transition-all duration-200"
                  : "cursor-default"
              }`}
            >
              <div className="flex flex-col items-start justify-start p-3 w-full h-full">
                {/* Exam Count */}
                <div className="text-base font-semibold leading-tight">
                  {examCount === 0
                    ? "No Exams"
                    : `${examCount} ${examCount === 1 ? "Exam" : "Exams"}`}
                </div>

                {/* Conflict Indicator */}
                <div className="text-xs font-normal pt-1">
                  {conflicts === 0
                    ? "No conflicts"
                    : `${conflicts} ${conflicts === 1 ? "conflict" : "conflicts"}`}
                </div>
              </div>
            </div>
          );
        }}
      />

      {/* Legend (dynamic based on selected theme) */}
      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="font-semibold mb-3 text-sm">Density Legend</h3>
        <div className="flex gap-3 items-center flex-wrap text-sm">
          {(() => {
            const themeColors = colorThemes[theme] || colorThemes.gray;
            const levels = [0, 1, 2, 3, 4];

            const textColorFromBg = (bg: string) =>
              getReadableTextColorFromBg(bg);

            return levels.map((lvl) => {
              const bg = themeColors[lvl] || themeColors[0];
              const textColor = textColorFromBg(bg);
              let label = "";
              const safe = (n: number) =>
                Number.isFinite(n) ? Math.max(0, Math.floor(n)) : 0;
              const t1 = safe(thresholds.t1);
              const t2 = safe(thresholds.t2);
              const t3 = safe(thresholds.t3);

              if (lvl === 0) label = "No Exams";
              else if (lvl === 1) {
                // 1..t1 (if t1 < 1 show single "1")
                label = t1 >= 1 ? `1-${t1}` : `1`;
              } else if (lvl === 2) {
                const low = t1 + 1;
                const high = t2;
                label = high >= low ? `${low}-${high}` : `${low}`;
              } else if (lvl === 3) {
                const low = t2 + 1;
                const high = t3;
                label = high >= low ? `${low}-${high}` : `${low}`;
              } else {
                const low = t3 + 1;
                label = `${low}+`;
              }

              return (
                <div key={lvl} className="flex items-center gap-2">
                  <div
                    className="w-10 h-10 border-2 rounded"
                    style={{
                      backgroundColor: bg,
                      borderColor: "rgba(0,0,0,0.08)",
                    }}
                  />
                  {/* Keep label text readable on the white legend background */}
                  <span
                    className={
                      lvl === 4
                        ? "px-2 py-0.5 rounded text-sm font-medium"
                        : "text-sm"
                    }
                  >
                    {label}
                  </span>
                </div>
              );
            });
          })()}
        </div>
      </div>
    </div>
  );
}
