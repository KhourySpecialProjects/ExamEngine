"use client";

import { parseAsArrayOf, parseAsString, useQueryStates } from "nuqs";
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api/client";
import type { CompareItem } from "@/lib/api/schedules";
import {
  addColumn,
  assignColors,
  columnOrder,
  compareIds,
  isScheduleId,
  moveColumn,
  reorderColumn,
  setBaseline,
} from "@/lib/compare";
import { MAX_COMPARED } from "@/lib/scheduleSelection";

const urlParams = {
  ids: parseAsArrayOf(parseAsString),
  /** Links from before the baseline was always first; read once, then dropped. */
  base: parseAsString,
};

export interface CompareColumnState {
  id: string;
  /** Undefined while its summary loads. */
  item: CompareItem | undefined;
  /** Index into COLUMN_COLORS; follows the schedule when columns move. */
  color: number;
}

/**
 * The Compare page's columns, kept in the URL (`?ids=a,b,c`), and their
 * summaries. The first available column is the baseline and is shown first.
 * Summaries already loaded are kept, so reordering or removing a column
 * doesn't ask the server again.
 */
export function useCompare() {
  const [params, setParams] = useQueryStates(urlParams);
  const urlIds = compareIds(params.ids);
  const [items, setItems] = useState<Record<string, CompareItem>>({});
  const [error, setError] = useState<string | null>(null);
  const [colors, setColors] = useState<Readonly<Record<string, number>>>({});
  const [attempt, setAttempt] = useState(0);

  const itemFor = (id: string): CompareItem | undefined =>
    isScheduleId(id) ? items[id] : { schedule_id: id, status: "unavailable" };
  const missingKey = urlIds.filter((id) => !itemFor(id)).join(",");

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

  // An old `?base=` link: that column moves to the front.
  // biome-ignore lint/correctness/useExhaustiveDependencies: runs once per `base` in the URL
  useEffect(() => {
    if (params.base === null) return;
    setParams(
      {
        ids: setBaseline(urlIds, params.base.toLowerCase()),
        base: null,
      },
      { history: "replace" },
    );
  }, [params.base]);

  const isShown = (id: string) => itemFor(id)?.status === "ok";
  const ids = columnOrder(urlIds, isShown);
  const base = ids.find(isShown) ?? null;
  const loading = missingKey !== "" && error === null;

  // Colours are handed out once the columns have loaded (and so are in their
  // shown order), then stay with their schedule. Nothing coloured shows while
  // loading.
  const nextColors = loading ? colors : assignColors(ids, colors);
  if (nextColors !== colors) setColors(nextColors);

  const write = (nextIds: string[]) =>
    setParams({ ids: nextIds.length > 0 ? nextIds : null, base: null });

  const retry = useCallback(() => {
    setError(null);
    setAttempt((n) => n + 1);
  }, []);

  return {
    ids,
    columns: ids.map(
      (id, i): CompareColumnState => ({
        id,
        item: itemFor(id),
        color: nextColors[id] ?? i,
      }),
    ),
    base,
    loading,
    error,
    retry,
    setBaseline: (id: string) => write(setBaseline(ids, id)),
    move: (id: string, offset: -1 | 1) => write(moveColumn(ids, id, offset)),
    /** Drag and drop: `id` takes the place of `target`. */
    reorder: (id: string, target: string) =>
      write(reorderColumn(ids, id, target)),
    /** Several at once: each write replaces the whole URL state. */
    remove: (...gone: string[]) =>
      write(ids.filter((id) => !gone.includes(id))),
    /** When the page is full, columns that can't be shown make room. */
    add: (id: string) => {
      const kept = ids.length >= MAX_COMPARED ? ids.filter(isShown) : ids;
      write(addColumn(kept, id.toLowerCase()));
    },
  };
}
