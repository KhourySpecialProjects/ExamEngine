import { AlertCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import type { Exam } from "@/lib/store/calendarStore";

interface ExamCardProps {
  exam: Exam;
  onClick?: () => void;
}

export function ExamCard({ exam, onClick }: ExamCardProps) {
  const hasConflict = exam.conflicts > 0;

  return (
    <Card
      onClick={onClick}
      className={`p-3 ${onClick ? "cursor-pointer hover:shadow-md" : ""} ${
        hasConflict ? "border-red-400 bg-red-50" : ""
      }`}
    >
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h3 className="font-bold text-sm">{exam.courseCode}</h3>
          <p className="text-xs text-muted-foreground">
            Section {exam.section}
          </p>
        </div>
        {hasConflict && (
          <Badge variant="destructive" className="gap-1">
            <AlertCircle className="h-3 w-3" />
            {exam.conflicts}
          </Badge>
        )}
      </div>

      {/* Exam Details */}
      <div className="text-xs">
        <div>Room: {exam.room}</div>
        <div>Enrollments: {exam.studentCount} students</div>
        <div>Instructor: {exam.instructor}</div>
      </div>
    </Card>
  );
}
