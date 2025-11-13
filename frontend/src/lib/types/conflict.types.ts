export interface conflictMap {
    conflictType: string;
    instructorConflicts: number;
    studentConflicts: number;
    backToBack: boolean;
    instructorBackToBack: boolean;
    overMaxExams: boolean;
}