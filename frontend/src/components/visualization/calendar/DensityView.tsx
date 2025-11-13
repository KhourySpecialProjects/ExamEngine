import { useMemo } from "react";
import { User, Users } from "lucide-react";
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
import { Badge } from "@/components/ui/badge";
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
  const { hasData, isLoading, calendarRows, schedule } = useScheduleData();
  const selectCell = useCalendarStore((state) => state.selectCell);
  const theme = useCalendarStore((s) => s.colorTheme || "gray");
  const setTheme = useCalendarStore((s) => s.setColorTheme);
  const thresholds = useMemo(() => {
    const counts = calendarRows.flatMap((row) =>
      row.days.map((d) => d.examCount),
    );
    return calculateThresholds(counts);
  }, [calendarRows]);

  const extractTimeFromBlock = (blockStr: string): string => {
    if (!blockStr) return "";
    if (!blockStr.includes("(")) return blockStr;
    const match = blockStr.match(/\(([^)]+)\)/);
    return match ? match[1] : blockStr;
  };

  // Build a map from frontendDay-normalizedTime -> array of conflict type strings
  const breakdownMap = useMemo(() => {
    const map = new Map<string, string[]>();
    const bd: any[] = schedule?.conflicts?.breakdown ?? [];
    if (!bd || bd.length === 0) return map;

    const dayNameMap: Record<string, string> = {
      Mon: "Monday",
      Tue: "Tuesday",
      Wed: "Wednesday",
      Thu: "Thursday",
      Fri: "Friday",
      Sat: "Saturday",
      Sun: "Sunday",
    };

    for (const conf of bd) {
      try {
        const backendDay = conf.day || "";
        const frontendDay = dayNameMap[backendDay] || backendDay || "";
        let rawBlock = conf.block_time || conf.blocks || conf.block || "";

        // If backend provides a numeric block index (e.g. '2'), try to resolve it to the
        // calendar row's timeSlot (like '2 (2:00-4:00)') so normalization matches cell.timeSlot
        if (rawBlock && /^\d+$/.test(String(rawBlock))) {
          const blockNum = String(rawBlock);
          // find a matching timeSlot in calendarRows
          const matched = calendarRows.find((r) => String(r.timeSlot).startsWith(`${blockNum} `) || String(r.timeSlot).startsWith(`${blockNum}(`) || String(r.timeSlot) === blockNum);
          if (matched) {
            rawBlock = matched.timeSlot;
          }
        }

        const normalized = extractTimeFromBlock(rawBlock);
        if (!frontendDay || !normalized) continue;
        const key = `${frontendDay}-${normalized}`;
        const t = conf.conflict_type || conf.type || conf.violation || String(conf);
        if (!t) continue;
        const arr = map.get(key) || [];
        arr.push(t);
        map.set(key, arr);
      } catch (e) {
        // ignore malformed entries
      }
    }

    return map;
  }, [schedule, calendarRows]);

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
          const conflictsNum = cell ? cell.conflicts || 0 : 0;
          const themeColors = colorThemes[theme] || colorThemes.gray;
          const { bg, color } = getDensityColor(
            cell ? cell.examCount : 0,
            thresholds,
            themeColors,
          );

          // Only detect student double-book conflicts (ignore all other types)
          const cellAny = cell as any;
          const conflictListRaw: any[] =
            (cellAny && (cellAny.conflictList || cellAny.conflicts_list || cellAny.conflict_details || cellAny.conflictDetails || cellAny.conflicts_detail)) || [];

          let conflictTypes: string[] = (conflictListRaw || [])
            .map((c: any) => (c && (c.conflict_type || c.type || c.violation || String(c))))
            .filter(Boolean);

          if (conflictTypes.length === 0 && cell) {
            const key = `${(cell as any).day}-${extractTimeFromBlock((cell as any).timeSlot)}`;
            const fromBd = breakdownMap.get(key) || [];
            conflictTypes = fromBd.slice();
          }

          // Filter to only student double-book identifiers (be permissive)
          const doubleTypes = conflictTypes.filter((t) => /double/i.test(String(t)) || String(t).toLowerCase().includes("student_double_book"));
          const doubleCount = doubleTypes.length;
          // Detect instructor double-book identifiers as well
          const instructorTypes = conflictTypes.filter((t) => /instructor/i.test(String(t)) || String(t).toLowerCase().includes("instructor_double_book"));
          const instructorCount = instructorTypes.length;

          // If backend provides a per-cell hard count for double books, prefer that (not typical)
          const displayDouble = doubleCount > 0 ? doubleCount : 0;
          const displayInstructor = instructorCount > 0 ? instructorCount : 0;

          return (
            <div
              onClick={() => examCount > 0 && cell && selectCell(cell)}
              style={{ backgroundColor: bg, color }}
              className={`w-full h-full flex items-center border border-gray-200 ${
                examCount > 0
                  ? "cursor-pointer hover:shadow-lg hover:z-10 relative transition-all duration-200"
                  : "cursor-default relative"
              }`}
            >
              {/* Compact double-book / instructor badge overlay (top-right) */}
              {(displayDouble > 0 || displayInstructor > 0) && (
                <div className="absolute top-2 right-2 z-20 flex items-center gap-1">
                  {displayInstructor > 0 && (
                    <span
                      className="inline-flex items-center gap-1 bg-amber-600 text-white text-xs font-medium rounded-full px-2 py-0.5 shadow"
                      title={`${displayInstructor} instructor double-book conflict${displayInstructor > 1 ? "s" : ""}`}
                      aria-label={`${displayInstructor} instructor double-book conflict${displayInstructor > 1 ? "s" : ""}`}
                    >
                      <Users className="h-3 w-3" />
                      {displayInstructor}
                    </span>
                  )}

                  {displayDouble > 0 && (
                    <span
                      className="inline-flex items-center gap-1 bg-red-600 text-white text-xs font-medium rounded-full px-2 py-0.5 shadow"
                      title={`${displayDouble} student double-book conflict${displayDouble > 1 ? "s" : ""}`}
                      aria-label={`${displayDouble} student double-book conflict${displayDouble > 1 ? "s" : ""}`}
                    >
                      <User className="h-3 w-3" />
                      {displayDouble}
                    </span>
                  )}
                </div>
              )}

              <div className="flex flex-col items-start justify-start p-3 w-full h-full">
                {/* Exam Count */}
                <div className="text-base font-semibold leading-tight">
                  {examCount === 0
                    ? "No Exams"
                    : `${examCount} ${examCount === 1 ? "Exam" : "Exams"}`}
                </div>

                {/* Conflict Indicator: only student double-book */}
                <div className="text-xs font-normal pt-1">
                  {displayDouble > 0 ? (
                    <div className="sr-only">
                      {/* kept for screen-readers; visible badge is shown as overlay */}
                      <span>{`${displayDouble} student double-book conflict${displayDouble > 1 ? "s" : ""}`}</span>
                    </div>
                  ) : null}
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
      {/* Conflict Legend: Student + Instructor Double-Book */}
      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="font-semibold mb-3 text-sm">Conflict Legend</h3>
        <div className="flex gap-3 items-center flex-wrap text-sm">
          {(() => {
            // detect student and instructor double-book presence in schedule-level breakdown and per-cell lists
            let foundStudent = false;
            let foundInstructor = false;

            for (const arr of Array.from(breakdownMap.values())) {
              for (const t of arr) {
                const s = String(t).toLowerCase();
                if (/double/.test(s) || s.includes("student_double_book")) foundStudent = true;
                if (/instructor/.test(s) || s.includes("instructor_double_book")) foundInstructor = true;
              }
            }

            // also scan per-cell explicit lists
            for (const row of calendarRows) {
              for (const d of row.days) {
                const dAny = d as any;
                const list = (dAny && (dAny.conflictList || dAny.conflicts_list || dAny.conflict_details || dAny.conflictDetails || dAny.conflicts_detail)) || [];
                for (const c of list) {
                  const t = c && (c.conflict_type || c.type || c.violation || String(c));
                  if (!t) continue;
                  const s = String(t).toLowerCase();
                  if (/double/.test(s) || s.includes("student_double_book")) foundStudent = true;
                  if (/instructor/.test(s) || s.includes("instructor_double_book")) foundInstructor = true;
                }
              }
            }

            if (!foundStudent && !foundInstructor) {
              return <div className="text-sm text-muted-foreground">No double-book conflicts detected</div>;
            }

            const items: any[] = [];
            if (foundStudent) {
              items.push(
                <div key="student" className="flex items-center gap-2">
                  <div
                    className="w-8 h-8 border-2 rounded flex items-center justify-center"
                    style={{ backgroundColor: "#ef4444", borderColor: "rgba(0,0,0,0.08)" }}
                  >
                    <User className="h-4 w-4 text-white" />
                  </div>
                  <span className="text-sm">Student Double-Book</span>
                </div>,
              );
            }

            if (foundInstructor) {
              items.push(
                <div key="instructor" className="flex items-center gap-2">
                  <div
                    className="w-8 h-8 border-2 rounded flex items-center justify-center"
                    style={{ backgroundColor: "#f97316", borderColor: "rgba(0,0,0,0.08)" }}
                  >
                    <Users className="h-4 w-4 text-white" />
                  </div>
                  <span className="text-sm">Instructor Double-Book</span>
                </div>,
              );
            }

            return items;
          })()}
        </div>
      </div>
    </div>
  );
}
