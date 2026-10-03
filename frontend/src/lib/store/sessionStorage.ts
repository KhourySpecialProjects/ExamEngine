import type { StateStorage } from "zustand/middleware";

/** Rows-per-page choices offered by every paginated table. */
export const PAGE_SIZES = [10, 25, 50, 100];

// sessionStorage calls can throw (storage blocked, quota exceeded). Zustand
// only guards obtaining the storage object, and a throwing setItem would
// escape the setter. Degrade to in-memory state instead.
export const safeSessionStorage: StateStorage = {
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
