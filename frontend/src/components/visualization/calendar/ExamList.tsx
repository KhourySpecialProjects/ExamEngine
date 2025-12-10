import { Calendar } from "lucide-react";
import type { Exam } from "@/lib/types/calendar.types";
import { ExamCard } from "./ExamCard";

interface ExamListProps {
  exams: Exam[];
  isMerged?: (crn: string) => boolean;
}

export function ExamList({ exams, isMerged }: ExamListProps) {
  if (exams.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <Calendar className="mx-auto h-12 w-12 mb-3 opacity-50" />
        <p>No exams scheduled</p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto space-y-3 pr-2">
      {exams.map((exam) => (
        <ExamCard 
          key={exam.id} 
          exam={exam} 
          isMerged={isMerged ? isMerged(exam.section) : false}
        />
      ))}
    </div>
  );
}
