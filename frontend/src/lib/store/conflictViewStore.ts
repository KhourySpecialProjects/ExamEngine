import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import type { ConflictViewState } from "@/lib/types/conflict.types";

export const CONFLICT_PAGE_SIZES = [10, 25, 50, 100];

// sessionStorage: the choice lasts for the browser session only.
export const useConflictViewStore = create<ConflictViewState>()(
  persist(
    (set) => ({
      pageSize: CONFLICT_PAGE_SIZES[0],
      setPageSize: (pageSize) => set({ pageSize }),
    }),
    {
      name: "conflict-view-storage",
      storage: createJSONStorage(() => sessionStorage),
    },
  ),
);
