import { create } from "zustand";
import type {CalendarState} from "@/lib/types/calendar.types"


export const useCalendarStore = create<CalendarState>((set) => ({
  // Initial state
  filters: {
    searchQuery: "",
  },
  selectedCell: null,
  colorTheme: "gray",

  // Filter actions
  setSearchQuery: (query) => {
    set((state) => ({
      filters: { ...state.filters, searchQuery: query },
    }));
  },

  setDepartmentFilter: (department) => {
    set((state) => ({
      filters: { ...state.filters, departmentFilter: department },
    }));
  },

  setShowConflictsOnly: (show) => {
    set((state) => ({
      filters: { ...state.filters, showConflictsOnly: show },
    }));
  },

  clearFilters: () => {
    set({
      filters: {
        searchQuery: "",
      },
    });
  },

  // Selection
  selectCell: (cell) => {
    set({ selectedCell: cell });
  },
  setColorTheme: (theme) => {
    set({ colorTheme: theme });
  },
}));
