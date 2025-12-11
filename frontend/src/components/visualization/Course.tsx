import { AlertCircle, GitMerge } from "lucide-react";
import { useMemo } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface CourseProps {
  title: string;
  students: string;
  building: string;
  className?: string;
  hasConflict?: boolean;
  isMerged?: boolean;
}

const colors = ["red", "blue", "green"] as const;

export function Course({
  title,
  students,
  building,
  className,
  hasConflict = false,
  isMerged = false,
}: CourseProps) {
  const color = useMemo(() => {
    return colors[Math.floor(Math.random() * colors.length)];
  }, []);

  const stud_title = `${students} students`;

  return (
    <Button
      variant={
        color as
          | "link"
          | "default"
          | "red"
          | "blue"
          | "yellow"
          | "green"
          | "ghost"
          | null
          | undefined
      }
      size="sm"
      className={`${className} ${hasConflict ? "border-red-400 bg-red-50" : ""} ${isMerged ? "border-blue-300 bg-blue-50/30" : ""} border-2 flex flex-col items-start gap-y-0 py-8 w-full no-underline relative`}
    >
      <div className="flex items-center justify-between w-full">
        <div className="flex items-center gap-2">
          <span className="font-bold">{title}</span>
        </div>

        {isMerged && (
          <Badge
            variant="outline"
            className="gap-1 border-blue-300 text-blue-700 bg-blue-50/50 ml-2"
            title="Merged course"
          >
            <GitMerge className="h-3 w-3" />
          </Badge>
        )}
        {hasConflict && (
          <Badge variant="destructive" className="gap-1 ml-2">
            <AlertCircle className="h-3 w-3" />
          </Badge>
        )}
      </div>
      <span className="text-xs">{stud_title}</span>
      <span className="text-xs">{building}</span>
    </Button>
  );
}
