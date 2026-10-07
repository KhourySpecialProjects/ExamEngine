import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import type { PersonKind } from "@/lib/api/schedules";
import { safeSessionStorage } from "./sessionStorage";

/** IDs a Recent list keeps, newest first. */
export const RECENT_PEOPLE = 5;

/** The ID looked up for one kind in one schedule, and the recent ones. */
export interface PersonPick {
  current: string | null;
  recent: string[];
}

export const NO_PICK: PersonPick = { current: null, recent: [] };

/**
 * Student and instructor IDs looked up in the Explore tab, per schedule. They
 * are kept in sessionStorage instead of the URL so they never reach browser
 * history or a shared link; they last until the browser tab is closed.
 */
export interface ExplorePeopleState {
  /** Schedule ID -> kind -> pick. */
  people: Record<string, Partial<Record<PersonKind, PersonPick>>>;
  /** Look up `id`: it becomes current and moves to the top of Recent. */
  pick: (scheduleId: string, kind: PersonKind, id: string) => void;
}

const isPick = (value: unknown): value is PersonPick => {
  const pick = value as PersonPick | null;
  return (
    typeof pick === "object" &&
    pick !== null &&
    (pick.current === null || typeof pick.current === "string") &&
    Array.isArray(pick.recent) &&
    pick.recent.every((id) => typeof id === "string")
  );
};

// Hydration is manual (the schedule page calls `persist.rehydrate()` after
// mounting), like `schedulesViewStore`: the server renders no picks.
export const useExplorePeopleStore = create<ExplorePeopleState>()(
  persist(
    (set) => ({
      people: {},
      pick: (scheduleId, kind, id) =>
        set((state) => {
          const recent = state.people[scheduleId]?.[kind]?.recent ?? [];
          const pick: PersonPick = {
            current: id,
            recent: [id, ...recent.filter((r) => r !== id)].slice(
              0,
              RECENT_PEOPLE,
            ),
          };
          return {
            people: {
              ...state.people,
              [scheduleId]: { ...state.people[scheduleId], [kind]: pick },
            },
          };
        }),
    }),
    {
      name: "explore-people-storage",
      storage: createJSONStorage(() => safeSessionStorage),
      skipHydration: true,
      partialize: (state) => ({ people: state.people }),
      // Keep only well-formed picks: the stored value may be stale or edited.
      merge: (persisted, current) => {
        const stored = (persisted as Partial<ExplorePeopleState> | undefined)
          ?.people;
        if (typeof stored !== "object" || stored === null) return current;
        const people: ExplorePeopleState["people"] = {};
        for (const [scheduleId, kinds] of Object.entries(stored)) {
          const picks: Partial<Record<PersonKind, PersonPick>> = {};
          for (const kind of ["student", "instructor"] as const) {
            const pick = kinds?.[kind];
            if (isPick(pick)) {
              picks[kind] = {
                current: pick.current,
                recent: pick.recent.slice(0, RECENT_PEOPLE),
              };
            }
          }
          people[scheduleId] = picks;
        }
        return { ...current, people };
      },
    },
  ),
);
