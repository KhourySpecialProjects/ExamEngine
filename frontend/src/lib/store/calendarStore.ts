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

export interface CalendarStats {
  totalExams: number;
  totalConflicts: number;
}

interface CalendarStore {
  scheduleData: CalendarRow[];
  allExams: Exam[];

  filters: CalendarFilters;

  selectedCell: CalendarCell | null;

  setScheduleData: (data: CalendarRow[]) => void;
  setSearchQuery: (query: string) => void;
  setDepartmentFilter: (department: string) => void;
  setShowConflictsOnly: (show: boolean) => void;
  clearFilters: () => void;
  selectCell: (cell: CalendarCell | null) => void;

  getFilteredExams: () => Exam[];
  getStats: () => CalendarStats;
  getDepartments: () => string[];
}

export const useCalendarStore = create<CalendarStore>((set, get) => ({
  // States
  scheduleData: [] as CalendarRow[],
  allExams: [],
  filters: {
    searchQuery: "",
    departmentFilter: "",
    showConflictsOnly: false,
  },
  selectedCell: null,

  setScheduleData: (data) => {
    const allExams: Exam[] = data.flatMap((row) =>
      row.days.flatMap((day) => day.exams),
    );
    set({ scheduleData: data, allExams });
  },

  setSearchQuery: (query) => {
    set((state) => ({
      filters: { ...state.filters, searchQuery: query },
    }));
  },

  setDepartmentFilter: (department: string) => {
    set((state) => ({
      filters: { ...state.filters, departmentFilter: department },
    }));
  },

  setShowConflictsOnly: (show: boolean) => {
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
  selectCell: (cell) => {
    set({ selectedCell: cell });
  },
  getFilteredExams: () => {
    const { allExams, filters } = get();

    return allExams.filter((exam) => {
      if (filters.searchQuery) {
        const query = filters.searchQuery.toLowerCase();
        const matchesSearch =
          exam.courseCode.toLowerCase().includes(query) ||
          exam.instructor.toLowerCase().includes(query) ||
          exam.room.toLowerCase().includes(query);

        if (!matchesSearch) return false;
      }

      if (
        filters.departmentFilter &&
        exam.department !== filters.departmentFilter
      ) {
        return false;
      }

      // Conflicts filter
      if (filters.showConflictsOnly && exam.conflicts === 0) {
        return false;
      }

      return true;
    });
  },
  getStats: () => {
    const { allExams } = get();

    const totalExams = allExams.length;
    const totalConflicts = allExams.reduce(
      (sum, exam) => sum + exam.conflicts,
      0,
    );

    return {
      totalExams,
      totalConflicts,
    };
  },
  getDepartments: () => {
    const { allExams } = get();
    return [...new Set(allExams.map((e) => e.department))].sort();
  },
}));
