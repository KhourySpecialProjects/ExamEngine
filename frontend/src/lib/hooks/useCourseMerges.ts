import { useState, useEffect } from "react";
import { apiClient } from "@/lib/api/client";

/**
 * Hook to fetch and cache course merge information for a dataset
 */
export function useCourseMerges(datasetId: string | null | undefined) {
  const [merges, setMerges] = useState<Record<string, string[]>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!datasetId) {
      setMerges({});
      return;
    }

    setIsLoading(true);
    setError(null);
    apiClient.datasets
      .getCourseMerges(datasetId)
      .then((data) => {
        const mergesData = data || {};
        console.log("[useCourseMerges] Loaded merges:", mergesData);
        setMerges(mergesData);
        setIsLoading(false);
      })
      .catch((err) => {
        console.error("[useCourseMerges] Error loading merges:", err);
        setError(err instanceof Error ? err.message : "Failed to load merges");
        setMerges({});
        setIsLoading(false);
      });
  }, [datasetId]);

  /**
   * Check if a CRN is part of any merge group
   * Handles string comparison with normalization
   */
  const isMerged = (crn: string): boolean => {
    if (!crn || Object.keys(merges).length === 0) {
      return false;
    }
    const normalizedCrn = String(crn).trim();
    const result = Object.values(merges).some((group) => 
      Array.isArray(group) && group.some((mergedCrn) => String(mergedCrn).trim() === normalizedCrn)
    );
    if (result) {
      console.log(`[useCourseMerges] CRN ${normalizedCrn} is merged`, merges);
    }
    return result;
  };

  /**
   * Get the merge group that contains a CRN, or null if not merged
   */
  const getMergeGroup = (crn: string): string[] | null => {
    for (const group of Object.values(merges)) {
      if (group.includes(crn)) {
        return group;
      }
    }
    return null;
  };

  return {
    merges,
    isMerged,
    getMergeGroup,
    isLoading,
    error,
  };
}

