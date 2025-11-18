import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";

import { ExamList } from "./ExamList";
import { ExamCard } from "./ExamCard";

vi.mock("./ExamCard", () => ({
  ExamCard: ({ exam }: any) => <div data-testid="exam-card">{exam.courseCode}</div>,
}));

describe("ExamList", () => {
  const baseExam = {
    id: "1",
    courseCode: "CS101",
    section: "A",
    room: "101",
    instructor: "John",
    studentCount: 30,
    conflicts: 0,
    department: "Computer Science",
    building: "Main Hall",
    day: "Monday",
    timeSlot: "09:00 AM - 11:00 AM",
  };

  it("renders empty state when no exams are provided", () => {
    render(<ExamList exams={[]} />);

    expect(screen.getByText("No exams scheduled")).toBeInTheDocument();

    const calendarIcon = document.querySelector("svg");
    expect(calendarIcon).toBeInTheDocument();
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

    expect(screen.getByText("CS101")).toBeInTheDocument();
    expect(screen.getByText("MATH200")).toBeInTheDocument();
    expect(screen.getByText("BIO150")).toBeInTheDocument();
  });

  it("wraps the exam list in the correct container", () => {
    const exams = [baseExam];

    const { container } = render(<ExamList exams={exams} />);

    const wrapper = container.querySelector(".overflow-y-auto");
    expect(wrapper).toBeInTheDocument();
  });
});
