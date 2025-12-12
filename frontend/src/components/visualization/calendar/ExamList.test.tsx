import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";

import { ExamList } from "./ExamList";

vi.mock("./ExamCard", () => ({
  ExamCard: ({ exam }: any) => <div data-testid="exam-card">{exam.courseCode}</div>,
}));

describe("ExamList", () => {
  const baseExam = {
    id: "1",
    courseCode: "CS2800",
    section: "A",
    room: "101",
    instructor: "Dr. Pats",
    studentCount: 30,
    conflicts: 0,
    department: "Computer Science",
    building: "Dodge Hall",
    day: "Monday",
    timeSlot: "09:00 AM - 11:00 AM",
  };

  it("renders empty state when no exams are provided", () => {
    render(<ExamList exams={[]} />);

    expect(screen.getByText("No exams scheduled")).toBeDefined();

    const calendarIcon = document.querySelector("svg");
    expect(calendarIcon).toBeDefined();
  });

  it("renders the correct number of ExamCard components", () => {
    const exams = [
      baseExam,
      { ...baseExam, id: "2", courseCode: "MATH200" },
      { ...baseExam, id: "3", courseCode: "BIO150" },
    ];

    render(<ExamList exams={exams} />);

    const cards = screen.getAllByTestId("exam-card");
    expect(cards).toHaveLength(3);

    expect(screen.getByText("CS2800")).toBeDefined();
    expect(screen.getByText("MATH200")).toBeDefined();
    expect(screen.getByText("BIO150")).toBeDefined();
  });

  it("wraps the exam list in the correct container", () => {
    const exams = [baseExam];

    const { container } = render(<ExamList exams={exams} />);

    const wrapper = container.querySelector(".overflow-y-auto");
    expect(wrapper).toBeDefined();
  });
});
