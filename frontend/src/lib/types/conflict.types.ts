export interface conflictMap {
    conflictType: string;
    instructorConflicts: number;
    studentConflicts: number;
    backToBack: boolean;
    instructorBackToBack: boolean;
    overMaxExams: boolean;
};

export interface ConflictMetrics {
  hard_student_conflicts: number;
  hard_instructor_conflicts: number;
  students_back_to_back: number;
  instructors_back_to_back: number;
  large_courses_not_early: number;
  student_gt3_per_day: number;
};