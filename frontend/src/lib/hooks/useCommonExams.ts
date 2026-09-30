import { useCallback, useEffect, useMemo, useState } from "react";
import { apiClient } from "@/lib/api/client";

/**
 * Fetch the common exam groups (same time block, different rooms) for a
 * dataset.
 *
 * Pass the dataset's combined exams (`merges`) to apply the closure rule: a
 * combined exam with any CRN listed in a common group belongs to that group
 * as a whole, so every one of its CRNs reports `isCommon`.
 */
export function useCommonExams(
  datasetId: string | null | undefined,
  merges?: Record<string, string[]>,
) {
  const [commonGroups, setCommonGroups] = useState<Record<string, string[]>>(
    {},
  );
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!datasetId) {
      setCommonGroups({});
      return;
    }

    let cancelled = false;
    setIsLoading(true);
    setError(null);
    apiClient.datasets
      .getCommonExams(datasetId)
      .then((data) => {
        if (!cancelled) setCommonGroups(data || {});
      })
      .catch((err) => {
        if (cancelled) return;
        setError(
          err instanceof Error ? err.message : "Failed to load common exams",
        );
        setCommonGroups({});
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [datasetId]);

  const commonCrns = useMemo(() => {
    const crns = new Set<string>();
    for (const group of Object.values(commonGroups)) {
      if (!Array.isArray(group)) continue;
      for (const crn of group) crns.add(String(crn).trim());
    }
    for (const group of Object.values(merges ?? {})) {
      if (!Array.isArray(group)) continue;
      const members = group.map((crn) => String(crn).trim());
      if (members.some((crn) => crns.has(crn))) {
        for (const crn of members) crns.add(crn);
      }
    }
    return crns;
  }, [commonGroups, merges]);

  const isCommon = useCallback(
    (crn: string): boolean => !!crn && commonCrns.has(String(crn).trim()),
    [commonCrns],
  );

  return {
    commonGroups,
    isCommon,
    isLoading,
    error,
  };
}
