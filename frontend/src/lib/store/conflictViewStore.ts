import { create } from "zustand";
import {
  createJSONStorage,
  persist,
  type StateStorage,
} from "zustand/middleware";
import type { ConflictViewState } from "@/lib/types/conflict.types";

export const CONFLICT_PAGE_SIZES = [10, 25, 50, 100];

// sessionStorage calls can throw (storage blocked, quota exceeded). Zustand
// only guards obtaining the storage object, and a throwing setItem would
// escape setPageSize. Degrade to in-memory state instead.
const safeSessionStorage: StateStorage = {
  getItem: (name) => {
    try {
      return sessionStorage.getItem(name);
    } catch {
      return null;
    }
  },
  setItem: (name, value) => {
    try {
      sessionStorage.setItem(name, value);
    } catch {
      // Not persisted; the in-memory value still applies.
    }
  },
  removeItem: (name) => {
    try {
      sessionStorage.removeItem(name);
    } catch {
      // Nothing to clean up if storage is unavailable.
    }
  },
};

// sessionStorage: the choice lasts for the browser session only.
export const useConflictViewStore = create<ConflictViewState>()(
  persist(
    (set) => ({
      pageSize: CONFLICT_PAGE_SIZES[0],
      setPageSize: (pageSize) => set({ pageSize }),
    }),
    {
      name: "conflict-view-storage",
      storage: createJSONStorage(() => safeSessionStorage),
      // Only accept an offered size: a stale or edited value such as 0 would
      // make the page count infinite.
      merge: (persisted, current) => {
        const size = (persisted as Partial<ConflictViewState> | undefined)
          ?.pageSize;
        return typeof size === "number" && CONFLICT_PAGE_SIZES.includes(size)
          ? { ...current, pageSize: size }
          : current;
      },
    },
  ),
);
