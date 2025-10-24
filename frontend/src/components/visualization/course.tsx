import * as React from "react";
import { Button } from "@/components/ui/button";

interface CourseProps {
  title: string;
  students: string;
  building: string;
  className?: string;
}

const colors = ["red", "blue", "green"] as const;

export function Course({ title, students, building, className }: CourseProps) {
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
      className={`${className} border-2 flex flex-col items-start gap-y-0 py-8 w-full no-underline`}
    >
      <span className="font-bold">{title}</span>
      <span className="text-xs">{stud_title}</span>
      <span className="text-xs">{building}</span>
    </Button>
  );
}
