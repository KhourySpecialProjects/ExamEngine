import type { Exam } from "@/lib/store/calendarStore";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface ExamCardProps {
  exam: Exam;
  showTimeSlot?: boolean;
}

export function ExamCard({ exam, showTimeSlot = false }: ExamCardProps) {
  const hasConflict = exam.conflicts > 0;

  return (
    <Card
      className={`p-2
        ${hasConflict ? "border-red-300 bg-red-50" : "border-border bg-card"}
      `}
    >
      {/* Exam Stats */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold text-lg">{exam.courseCode}</h3>
          <p className="text-sm text-muted-foreground">
            Section {exam.section}
          </p>
        </div>
        {hasConflict && <div>{exam.conflicts}</div>}
      </div>

      {/* Exam  Details */}
      <div className="grid grid-cols-2 gap-3 text-sm">
        Building:{exam.building}
        Room: {exam.room}
        Student Count: {exam.studentCount}
        Instructor: {exam.instructor}
      </div>
    </Card>
  );
}
