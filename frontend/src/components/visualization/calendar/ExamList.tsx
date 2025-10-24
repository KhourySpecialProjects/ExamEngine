import { Calendar } from "lucide-react";
import type { Exam } from "@/lib/store/calendarStore";
import { ExamCard } from "./ExamCard";

interface ExamListProps {
  exams: Exam[];
}

export function ExamList({ exams }: ExamListProps) {
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
        <ExamCard key={exam.id} exam={exam} />
      ))}
    </div>
  );
}
