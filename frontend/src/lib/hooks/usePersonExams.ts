import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api/client";
import type { PersonExamsResult, PersonKind } from "@/lib/api/schedules";

export interface PersonExamsState {
  result: PersonExamsResult | null;
  error: string | null;
  isLoading: boolean;
}

/**
 * One student's or instructor's exams in a schedule. Refetches when any
 * argument changes; a blank ID loads nothing. A reply to an earlier ID is
 * dropped.
 */
export function usePersonExams(
  scheduleId: string,
  kind: PersonKind,
  personId: string,
): PersonExamsState {
  const [state, setState] = useState<PersonExamsState>({
    result: null,
    error: null,
    isLoading: false,
  });

  useEffect(() => {
    const id = personId.trim();
    if (!id) {
      setState({ result: null, error: null, isLoading: false });
      return;
    }
    let current = true;
    setState({ result: null, error: null, isLoading: true });
    apiClient.schedules
      .personExams(scheduleId, kind, id)
      .then((result) => {
        if (current) setState({ result, error: null, isLoading: false });
      })
      .catch((err: unknown) => {
        if (current)
          setState({
            result: null,
            error: err instanceof Error ? err.message : "Unknown error",
            isLoading: false,
          });
      });
    return () => {
      current = false;
    };
  }, [scheduleId, kind, personId]);

  return state;
}
