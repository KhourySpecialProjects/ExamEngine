"use client";
import { useEffect } from "react";
import ListView from "@/components/visualization/list/ListView";
import { useCalendarStore } from "@/store/calendarStore";

const generateSampleData = () => {
  const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
  const timeSlots = [
    "8:00 - 10:00 AM",
    "10:30 AM - 12:30 PM",
    "1:00 - 3:00 PM",
    "3:30 - 5:30 PM",
    "6:00 - 8:00 PM",
  ];

  const departments = ["CS", "MATH", "PHYS", "CHEM", "EECE", "BUSN"];
  const buildings = ["WVH", "Shillman", "Kariotis", "Ryder", "Churchill"];

  const data: any = [];

  timeSlots.forEach((timeSlot) => {
    const row = { timeSlot, days: [] };

    days.forEach((day) => {
      const examCount = 270;
      const conflicts = examCount > 15 ? Math.floor(Math.random() * 120) : 0;

      const exams = [];
      for (let i = 0; i < examCount; i++) {
        const dept =
          departments[Math.floor(Math.random() * departments.length)];
        const building =
          buildings[Math.floor(Math.random() * buildings.length)];
        exams.push({
          id: `exam-${day}-${timeSlot}-${i}`,
          courseCode: `${dept} ${1000 + Math.floor(Math.random() * 4000)}`,
          section: `0${Math.floor(Math.random() * 5) + 1}`,
          department: dept,
          instructor: [
            "Dr. Smith",
            "Prof. Johnson",
            "Dr. Williams",
            "Prof. Davis",
          ][Math.floor(Math.random() * 4)],
          studentCount: 50 + Math.floor(Math.random() * 150),
          room: `${building} ${100 + Math.floor(Math.random() * 300)}`,
          building: building,
          conflicts: i < conflicts ? Math.floor(Math.random() * 3) + 1 : 0,
          day,
          timeSlot,
        });
      }

      row.days.push({ day, timeSlot, examCount, conflicts, exams });
    });

    data.push(row);
  });

  return data;
};
export default function DensityPage() {
  const setScheduleData = useCalendarStore((state) => state.setScheduleData);

  useEffect(() => {
    const data = generateSampleData();

    setScheduleData(data);
  }, [setScheduleData]);

  return (
    <div className="w-auto">
      <ListView />
    </div>
  );
}
