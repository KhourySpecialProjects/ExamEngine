import { create } from "zustand";

export interface Exam {
  id: string;
  courseCode: string;
  section: string;
  department: string;
  instructor: string;
  studentCount: number;
  room: string;
  building: string;
  conflicts: number;
  day: string;
  timeSlot: string;
}

export interface CalendarCell {
  day: string;
  timeSlot: string;
  examCount: number;
  conflicts: number;
  exams: Exam[];
}

export interface CalendarRow {
  timeSlot: string;
  days: CalendarCell[];
}

export interface CalendarFilters {
  searchQuery: string;
  departmentFilter: string;
  showConflictsOnly: boolean;
}

interface CalendarState {
  // Initial state
  filters: CalendarFilters;
  selectedCell: CalendarCell | null;

  // Actions
  setSearchQuery: (query: string) => void;
  setDepartmentFilter: (department: string) => void;
  setShowConflictsOnly: (show: boolean) => void;
  clearFilters: () => void;
  selectCell: (cell: CalendarCell | null) => void;
}

export const useCalendarStore = create<CalendarState>((set) => ({
  // Initial state
  filters: {
    searchQuery: "",
    departmentFilter: "",
    showConflictsOnly: false,
  },
  selectedCell: null,

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
        departmentFilter: "",
        showConflictsOnly: false,
      },
    });
  },

  // Selection
  selectCell: (cell) => {
    set({ selectedCell: cell });
  },
}));
