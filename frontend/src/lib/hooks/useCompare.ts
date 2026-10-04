"use client";

import { parseAsArrayOf, parseAsString, useQueryStates } from "nuqs";
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api/client";
import type { CompareItem } from "@/lib/api/schedules";
import {
  addColumn,
  baselineId,
  compareIds,
  isScheduleId,
  moveColumn,
} from "@/lib/compare";
import { MAX_COMPARED } from "@/lib/scheduleSelection";

const urlParams = {
  ids: parseAsArrayOf(parseAsString),
  base: parseAsString,
};

export interface CompareColumnState {
  id: string;
  /** Undefined while its summary loads. */
  item: CompareItem | undefined;
}

/**
 * The Compare page's columns and baseline, kept in the URL
 * (`?ids=a,b,c&base=a`), and their summaries. Summaries already loaded are
 * kept, so reordering or removing a column doesn't ask the server again.
 */
export function useCompare() {
  const [params, setParams] = useQueryStates(urlParams);
  const ids = compareIds(params.ids);
  const [items, setItems] = useState<Record<string, CompareItem>>({});
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  const itemFor = (id: string): CompareItem | undefined =>
    isScheduleId(id) ? items[id] : { schedule_id: id, status: "unavailable" };
  const missingKey = ids.filter((id) => !itemFor(id)).join(",");

  // biome-ignore lint/correctness/useExhaustiveDependencies: `attempt` re-runs a failed request
  useEffect(() => {
    if (!missingKey) return;
    let cancelled = false;
    setError(null);
    apiClient.schedules
      .compare(missingKey.split(","))
      .then(({ schedules }) => {
        if (cancelled) return;
        setItems((prev) => ({
          ...prev,
          ...Object.fromEntries(schedules.map((s) => [s.schedule_id, s])),
        }));
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Unknown error");
      });
    return () => {
      cancelled = true;
    };
  }, [missingKey, attempt]);

  const base = baselineId(
    ids,
    params.base?.toLowerCase() ?? null,
    (id) => itemFor(id)?.status === "ok",
  );

  const write = (nextIds: string[], nextBase: string | null) =>
    setParams({
      ids: nextIds.length > 0 ? nextIds : null,
      base: nextBase && nextIds.includes(nextBase) ? nextBase : null,
    });

  const retry = useCallback(() => {
    setError(null);
    setAttempt((n) => n + 1);
  }, []);

  return {
    ids,
    columns: ids.map((id): CompareColumnState => ({ id, item: itemFor(id) })),
    base,
    loading: missingKey !== "" && error === null,
    error,
    retry,
    setBaseline: (id: string) => write(ids, id),
    move: (id: string, offset: -1 | 1) =>
      write(moveColumn(ids, id, offset), base),
    /** Several at once: each write replaces the whole URL state. */
    remove: (...gone: string[]) =>
      write(
        ids.filter((id) => !gone.includes(id)),
        base && gone.includes(base) ? null : base,
      ),
    /** When the page is full, columns that can't be shown make room. */
    add: (id: string) => {
      const kept =
        ids.length >= MAX_COMPARED
          ? ids.filter((other) => itemFor(other)?.status === "ok")
          : ids;
      write(addColumn(kept, id.toLowerCase()), base);
    },
  };
}
