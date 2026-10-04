export interface conflictMap {
  conflictType: string;
  instructorConflicts: number;
  studentConflicts: number;
  backToBack: boolean;
  instructorBackToBack: boolean;
  overMaxExams: boolean;
}

/** Conflicts-view preferences kept for the browser session. */
export interface ConflictViewState {
  /** Rows per page in every conflict table. */
  pageSize: number;
  setPageSize: (size: number) => void;
}
