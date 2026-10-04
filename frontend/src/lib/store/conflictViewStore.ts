import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import type { ConflictViewState } from "@/lib/types/conflict.types";
import { PAGE_SIZES, safeSessionStorage } from "./sessionStorage";

// sessionStorage: the choice lasts for the browser session only.
export const useConflictViewStore = create<ConflictViewState>()(
  persist(
    (set) => ({
      pageSize: PAGE_SIZES[0],
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
        return typeof size === "number" && PAGE_SIZES.includes(size)
          ? { ...current, pageSize: size }
          : current;
      },
    },
  ),
);
