import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import { PAGE_SIZES, safeSessionStorage } from "./sessionStorage";

export type SchedulesView = "list" | "dataset";

/** Schedules-page preferences kept for the browser session. */
export interface SchedulesViewState {
  view: SchedulesView;
  setView: (view: SchedulesView) => void;
  /** Rows per page in the schedules list. */
  pageSize: number;
  setPageSize: (size: number) => void;
  /** Dataset groups per page in the By-dataset view. */
  datasetPageSize: number;
  setDatasetPageSize: (size: number) => void;
}

const offeredSize = (size: unknown): size is number =>
  typeof size === "number" && PAGE_SIZES.includes(size);

// sessionStorage: the choices last for the browser session only. Hydration is
// manual (the schedules page calls `persist.rehydrate()` after mounting): the
// server renders the defaults, and restoring before React hydrates would make
// the first client render differ from the server HTML.
export const useSchedulesViewStore = create<SchedulesViewState>()(
  persist(
    (set) => ({
      view: "list",
      setView: (view) => set({ view }),
      pageSize: PAGE_SIZES[0],
      setPageSize: (pageSize) => set({ pageSize }),
      datasetPageSize: PAGE_SIZES[0],
      setDatasetPageSize: (datasetPageSize) => set({ datasetPageSize }),
    }),
    {
      name: "schedules-view-storage",
      storage: createJSONStorage(() => safeSessionStorage),
      skipHydration: true,
      // Only accept known values: a stale or edited page size such as 0 would
      // make the page count infinite.
      merge: (persisted, current) => {
        const stored = (persisted ?? {}) as Partial<SchedulesViewState>;
        return {
          ...current,
          ...(stored.view === "list" || stored.view === "dataset"
            ? { view: stored.view }
            : {}),
          ...(offeredSize(stored.pageSize)
            ? { pageSize: stored.pageSize }
            : {}),
          ...(offeredSize(stored.datasetPageSize)
            ? { datasetPageSize: stored.datasetPageSize }
            : {}),
        };
      },
    },
  ),
);
