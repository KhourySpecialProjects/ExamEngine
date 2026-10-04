import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import { PAGE_SIZES, safeSessionStorage } from "./sessionStorage";

/** Schedules-page preferences kept for the browser session. */
export interface SchedulesViewState {
  /** Rows per page in the schedules list. */
  pageSize: number;
  setPageSize: (size: number) => void;
}

// sessionStorage: the choice lasts for the browser session only. Hydration is
// manual (the schedules page calls `persist.rehydrate()` after mounting): the
// server renders the defaults, and restoring before React hydrates would make
// the first client render differ from the server HTML.
export const useSchedulesViewStore = create<SchedulesViewState>()(
  persist(
    (set) => ({
      pageSize: PAGE_SIZES[0],
      setPageSize: (pageSize) => set({ pageSize }),
    }),
    {
      name: "schedules-view-storage",
      storage: createJSONStorage(() => safeSessionStorage),
      skipHydration: true,
      // Only accept an offered size: a stale or edited value such as 0 would
      // make the page count infinite.
      merge: (persisted, current) => {
        const size = (persisted as Partial<SchedulesViewState> | undefined)
          ?.pageSize;
        return typeof size === "number" && PAGE_SIZES.includes(size)
          ? { ...current, pageSize: size }
          : current;
      },
    },
  ),
);
