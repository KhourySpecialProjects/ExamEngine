import { useEffect, useRef, useState } from "react";
import { apiClient } from "@/lib/api/client";
import type { ScheduleRoomsResult } from "@/lib/api/schedules";

export interface ScheduleRoomsState {
  result: ScheduleRoomsResult | null;
  error: string | null;
  isLoading: boolean;
}

/**
 * A schedule's rooms with their blocked times. Loads once `enabled` is first
 * true (it reads the uploaded blockouts file, so only when needed) and keeps
 * the result for this schedule; a reply for an earlier schedule is dropped.
 */
export function useScheduleRooms(
  scheduleId: string,
  enabled: boolean,
): ScheduleRoomsState {
  const [state, setState] = useState<
    ScheduleRoomsState & { scheduleId: string | null }
  >({ scheduleId: null, result: null, error: null, isLoading: false });
  // The schedule whose rooms were requested (and not abandoned).
  const requested = useRef<string | null>(null);

  useEffect(() => {
    if (!enabled || requested.current === scheduleId) return;
    requested.current = scheduleId;
    let current = true;
    let done = false;
    setState({ scheduleId, result: null, error: null, isLoading: true });
    apiClient.schedules
      .rooms(scheduleId)
      .then((result) => {
        done = true;
        if (current)
          setState({ scheduleId, result, error: null, isLoading: false });
      })
      .catch((err: unknown) => {
        done = true;
        if (current)
          setState({
            scheduleId,
            result: null,
            error: err instanceof Error ? err.message : "Unknown error",
            isLoading: false,
          });
      });
    return () => {
      current = false;
      // An abandoned request is made again next time.
      if (!done) requested.current = null;
    };
  }, [scheduleId, enabled]);

  return state.scheduleId === scheduleId
    ? { result: state.result, error: state.error, isLoading: state.isLoading }
    : { result: null, error: null, isLoading: enabled };
}
