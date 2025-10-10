import * as React from "react"
import { Button } from "@/components/ui/button"

interface CourseProps {
  color: string 
  title: string
  students: string
  building: string
  className?: string
}

export function Course({ color, title, students, building, className }: CourseProps) {
    const stud_title = students + " students"
  return (
    <Button
      variant={color as "link" | "default" | "red" | "blue" | "yellow" | "green" | "ghost" | null | undefined}
      size="sm"
      className={`${className} border-2 hover:underline flex flex-col items-start gap-y-0 px-5 py-8`}
    >
    <span className="font-bold">{title}</span>
    <span className="text-xs">{stud_title}</span>
    <span className="text-xs">{building}</span>
    </Button>
  )
}