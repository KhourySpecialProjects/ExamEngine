import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";

import { ExamCard } from "./ExamCard";

describe("ExamCard", () => {
  const examBase = {
    id: "1",
    courseCode: "CS2800",
    section: "A",
    room: "Room 12",
    studentCount: 40,
    instructor: "Dr. Pats",
    conflicts: 0,
    department: "Computer Science",
    building: "Dodge Hall",
    day: "Monday",
    timeSlot: "10:00 AM - 12:00 PM",
  };

  it("renders exam information correctly", () => {
    render(<ExamCard exam={examBase} />);

    expect(screen.getByText("CS2800")).toBeDefined();
    expect(screen.getByText(/Section A/i)).toBeDefined();
    expect(screen.getByText("Room: Room 12")).toBeDefined();
    expect(screen.getByText(/40 students/)).toBeDefined();
    expect(screen.getByText(/Instructor: Dr\. Pats/)).toBeDefined();
  });

  it("does NOT show the conflict badge when conflicts = 0", () => {
    render(<ExamCard exam={examBase} />);

    expect(screen.queryByText("0")).toBeDefined();
  });

  it("shows a conflict badge when conflicts > 0", () => {
    const examConflict = { ...examBase, conflicts: 2 };

    render(<ExamCard exam={examConflict} />);

    expect(screen.getByText("2")).toBeDefined();

    const badge = screen.getByText("2").closest(".gap-1");
    expect(badge).toBeDefined();
  });

  it("applies conflict styles when conflicts > 0", () => {
    const examConflict = { ...examBase, conflicts: 1 };

    const { container } = render(<ExamCard exam={examConflict} />);

    const card = container.querySelector(".border-red-400");
    expect(card).toBeDefined();
  });

  it("fires onClick when the card is clicked", () => {
    const mock = vi.fn();

    render(<ExamCard exam={examBase} onClick={mock} />);

    const card = screen.getByText("CS2800").closest("div")?.parentElement;
    expect(card).toBeDefined();

    fireEvent.click(card!);

    expect(mock).toHaveBeenCalledOnce();
  });

  it("adds interactive styling when onClick is provided", () => {
    const { container } = render(<ExamCard exam={examBase} onClick={() => {}} />);

    const card = container.querySelector(".cursor-pointer");
    expect(card).toBeDefined();
  });
});
