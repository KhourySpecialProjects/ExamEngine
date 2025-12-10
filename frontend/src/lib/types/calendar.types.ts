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
  isUnscheduled?: boolean; // True if exam has no time slot or room assignment
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
}

export interface CalendarState {
  // Initial state
  filters: CalendarFilters;
  selectedCell: CalendarCell | null;
  // UI
  colorTheme: string;

  // Actions
  setSearchQuery: (query: string) => void;
  setDepartmentFilter: (department: string) => void;
  setShowConflictsOnly: (show: boolean) => void;
  clearFilters: () => void;
  selectCell: (cell: CalendarCell | null) => void;
  setColorTheme: (theme: string) => void;
}