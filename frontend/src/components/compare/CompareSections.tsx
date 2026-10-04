import {
  ChevronDown,
  ChevronRight,
  CircleCheck,
  CircleX,
  ExternalLink,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import type { FillBucket } from "@/lib/api/schedules";
import {
  CONFLICT_ROWS,
  compareSettings,
  countOf,
  type Delta,
  delta,
  formatDelta,
  publishBlockers,
} from "@/lib/compare";
import { scheduleHref } from "@/lib/scheduleView";
import { cn } from "@/lib/utils";
import { MiniBarChart } from "./CompareCharts";
import {
  CompareSection,
  MetricRow,
  shownColumns,
  useGridColumns,
} from "./CompareGrid";

const TONE_CLASSES: Record<Delta["tone"], string> = {
  better: "bg-emerald-50 text-emerald-700 border-emerald-200",
  worse: "bg-red-50 text-red-700 border-red-200",
  same: "bg-muted text-muted-foreground border-transparent",
};

const TONE_WORDS: Record<Delta["tone"], string> = {
  better: "better than the baseline",
  worse: "worse than the baseline",
  same: "same as the baseline",
};

function DeltaBadge({ value }: { value: Delta }) {
  return (
    <span
      className={cn(
        "inline-flex rounded border px-1.5 text-xs font-medium tabular-nums",
        TONE_CLASSES[value.tone],
      )}
      title={TONE_WORDS[value.tone]}
    >
      {formatDelta(value.value)}
      <span className="sr-only"> ({TONE_WORDS[value.tone]})</span>
    </span>
  );
}

export function SettingsSection() {
  const columns = shownColumns(useGridColumns());
  const [showSame, setShowSame] = useState(false);
  const { differing, same } = compareSettings(
    columns.map((c) => c.schedule.summary),
  );
  const rowOf = (key: string, id: string) => {
    const setting = [...differing, ...same].find((s) => s.key === key);
    return setting?.rows[columns.findIndex((c) => c.id === id)];
  };

  const settingRow = (key: string, label: string, marked: boolean) => (
    <MetricRow
      key={key}
      label={
        <span className="flex items-center gap-1.5">
          {marked && (
            <span className="font-semibold text-amber-600" title="Differs">
              ≠<span className="sr-only">Differs:</span>
            </span>
          )}
          {label}
        </span>
      }
      cell={(column) => {
        const row = rowOf(key, column.id);
        if (!row) return null;
        return (
          <div
            className={cn(
              "text-sm",
              row.unused ? "text-muted-foreground" : "font-medium",
            )}
          >
            {row.value}
            {row.note && (
              <span className="block text-xs font-normal text-muted-foreground">
                {row.note}
              </span>
            )}
          </div>
        );
      }}
    />
  );

  return (
    <CompareSection title="Settings">
      {differing.length === 0 && (
        <p className="py-3 text-sm text-muted-foreground">
          All schedules were generated with the same settings.
        </p>
      )}
      {differing.map((s) => settingRow(s.key, s.label, true))}
      {same.length > 0 && (
        <button
          type="button"
          className="flex items-center gap-1 py-3 text-sm text-muted-foreground hover:text-foreground"
          aria-expanded={showSame}
          onClick={() => setShowSame((open) => !open)}
        >
          {showSame ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
          Same in all ({same.length})
        </button>
      )}
      {showSame && same.map((s) => settingRow(s.key, s.label, false))}
    </CompareSection>
  );
}

export function PublishableSection() {
  return (
    <CompareSection title="Publishable?">
      <MetricRow
        label="Ready to publish"
        info="Yes when there are no hard conflicts (double-bookings or more exams in a day than allowed) and every exam has a time and a room that fits."
        cell={(column) => {
          const blockers = publishBlockers(column.schedule.summary);
          if (blockers.length === 0) {
            return (
              <span className="flex items-center gap-1.5 text-sm font-medium text-emerald-700">
                <CircleCheck className="h-4 w-4" aria-hidden />
                Yes
              </span>
            );
          }
          return (
            <div className="text-sm">
              <span className="flex items-center gap-1.5 font-medium text-red-700">
                <CircleX className="h-4 w-4" aria-hidden />
                No
              </span>
              <ul className="mt-1 space-y-0.5 text-xs text-muted-foreground">
                {blockers.map((b) => (
                  <li key={b.label}>
                    <span className="font-medium text-foreground tabular-nums">
                      {b.count.toLocaleString()}
                    </span>{" "}
                    {b.label}
                  </li>
                ))}
              </ul>
            </div>
          );
        }}
      />
    </CompareSection>
  );
}

export function ConflictsSection() {
  const columns = shownColumns(useGridColumns());
  const baseline = columns.find((c) => c.isBaseline);
  return (
    <CompareSection title="Conflicts">
      {CONFLICT_ROWS.map((row) => (
        <MetricRow
          key={row.metric}
          label={row.label}
          info={
            <>
              <p>{row.definition}</p>
              <p className="mt-2 text-muted-foreground">
                The first number counts distinct {row.unit[1]}; “times” counts
                each occurrence. Lower is better.
              </p>
            </>
          }
          cell={(column) => {
            const count = column.schedule.summary.conflicts[row.metric];
            const base =
              baseline && !column.isBaseline
                ? baseline.schedule.summary.conflicts[row.metric]
                : null;
            const people = countOf(count.people, row.unit);
            return (
              <div className="text-sm">
                <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                  {count.people > 0 ? (
                    // The schedule's Conflicts tab lists the same people.
                    <Link
                      href={scheduleHref(column.schedule.schedule_id, {
                        view: "conflicts",
                        type: row.type,
                      })}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 font-semibold tabular-nums underline-offset-2 hover:underline"
                      aria-label={`${people}: ${row.label} in ${column.schedule.schedule_name} (opens in a new tab)`}
                      title={`Open ${row.label} in ${column.schedule.schedule_name}`}
                    >
                      {people}
                      <ExternalLink
                        className="h-3 w-3 text-muted-foreground"
                        aria-hidden
                      />
                    </Link>
                  ) : (
                    <span className="font-semibold tabular-nums">{people}</span>
                  )}
                  {base && (
                    <DeltaBadge value={delta(count.people, base.people)} />
                  )}
                </div>
                <div className="text-xs text-muted-foreground tabular-nums">
                  {countOf(count.instances, ["time", "times"])}
                </div>
              </div>
            );
          }}
        />
      ))}
    </CompareSection>
  );
}

const FILL_BUCKETS: { key: FillBucket; label: string; title: string }[] = [
  { key: "under_50", label: "<50%", title: "Under 50% of seats filled" },
  { key: "from_50_to_75", label: "50–75", title: "50–75% of seats filled" },
  { key: "from_75_to_90", label: "75–90", title: "75–90% of seats filled" },
  { key: "from_90_to_100", label: "90+", title: "90–100% of seats filled" },
];

export function RoomsSection() {
  const columns = shownColumns(useGridColumns());
  const maxBucket = Math.max(
    0,
    ...columns.flatMap((c) =>
      FILL_BUCKETS.map((b) => c.schedule.summary.rooms.fill_buckets[b.key]),
    ),
  );
  return (
    <CompareSection title="Rooms">
      <MetricRow
        label="Rooms used"
        cell={(column) => (
          <span className="text-sm font-semibold tabular-nums">
            {column.schedule.summary.rooms.used.toLocaleString()}
          </span>
        )}
      />
      <MetricRow
        label="Average fill"
        info="Mean share of seats filled per placed exam, each capped at 100%."
        cell={(column) => (
          <span className="text-sm font-semibold tabular-nums">
            {column.schedule.summary.rooms.average_fill}%
          </span>
        )}
      />
      <MetricRow
        label="Fill distribution"
        hint={`Placed exams by seats filled; same scale (max ${maxBucket})`}
        cell={(column) => (
          <MiniBarChart
            data={FILL_BUCKETS.map((b) => ({
              label: b.label,
              title: b.title,
              value: column.schedule.summary.rooms.fill_buckets[b.key],
            }))}
            max={maxBucket}
            color={column.color.fill}
          />
        )}
      />
    </CompareSection>
  );
}
