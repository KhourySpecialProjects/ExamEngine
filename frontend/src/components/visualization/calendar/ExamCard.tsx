import { AlertCircle, GitMerge } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import type { Exam } from "@/lib/types/calendar.types";

interface ExamCardProps {
  exam: Exam;
  onClick?: () => void;
  isMerged?: boolean;
}

export function ExamCard({ exam, onClick, isMerged = false }: ExamCardProps) {
  const hasConflict = exam.conflicts > 0;

  return (
    <Card
      onClick={onClick}
      className={`p-3 ${onClick ? "cursor-pointer hover:shadow-md" : ""} ${
        hasConflict ? "border-red-400 bg-red-50" : ""
      } ${isMerged ? "border-2 border-blue-500 bg-blue-50" : ""}`}
    >
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-bold text-sm">{exam.courseCode}</h3>
            {isMerged && (
              <div className="flex items-center gap-1 text-blue-600" title="Merged course">
                <GitMerge className="h-4 w-4" />
              </div>
            )}
          </div>
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
