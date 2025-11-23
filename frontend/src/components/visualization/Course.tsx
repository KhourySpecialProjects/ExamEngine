import * as React from "react";
import { AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface CourseProps {
  title: string;
  students: string;
  building: string;
  className?: string;
  hasConflict?: boolean;
}

const colors = ["red", "blue", "green"] as const;

export function Course({ title, students, building, className, hasConflict = false }: CourseProps) {
  const color = React.useMemo(() => {
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
      className={`${className} ${hasConflict ? "border-red-400 bg-red-50" : ""} border-2 flex flex-col items-start gap-y-0 py-8 w-full no-underline relative`}
    >
      <div className="flex items-center justify-between w-full">
        <span className="font-bold">{title}</span>
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
