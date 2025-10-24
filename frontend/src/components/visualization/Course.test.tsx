import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Course } from "./Course";

describe("Course Component", () => {
  const defaultProps = {
    title: "CS 4535",
    students: "50",
    building: "Richards Hall 101",
  };

  it("renders course title correctly", () => {
    render(<Course {...defaultProps} />);
    const title = screen.getByText("CS 4535");
    expect(title).toBeDefined();
    expect(title.textContent).toBe("CS 4535");
  });

  it("renders student count with correct formatting", () => {
    render(<Course {...defaultProps} />);
    const students = screen.getByText("50 students");
    expect(students).toBeDefined();
    expect(students.textContent).toBe("50 students");
  });

  it("renders building information", () => {
    render(<Course {...defaultProps} />);
    const building = screen.getByText("Richards Hall 101");
    expect(building).toBeDefined();
    expect(building.textContent).toBe("Richards Hall 101");
  });

  it("applies custom className", () => {
    render(<Course {...defaultProps} className="custom-class" />);
    const button = screen.getByRole("button");
    expect(button.className).toContain("custom-class");
  });

  it("applies default styling classes", () => {
    render(<Course {...defaultProps} />);
    const button = screen.getByRole("button");
    expect(button.className).toContain("border-2");
    expect(button.className).toContain("hover:underline");
    expect(button.className).toContain("flex");
    expect(button.className).toContain("flex-col");
  });

  it("renders with different student counts", () => {
    render(<Course {...defaultProps} students="150" />);
    const students = screen.getByText("150 students");
    expect(students.textContent).toBe("150 students");
  });

  it("renders with different buildings", () => {
    render(<Course {...defaultProps} building="Snell Library 240" />);
    const building = screen.getByText("Snell Library 240");
    expect(building.textContent).toBe("Snell Library 240");
  });

  it("renders with different course titles", () => {
    render(<Course {...defaultProps} title="CS 3500" />);
    const title = screen.getByText("CS 3500");
    expect(title.textContent).toBe("CS 3500");
  });

  it("renders title with bold font", () => {
    render(<Course {...defaultProps} />);
    const title = screen.getByText("CS 4535");
    expect(title.className).toContain("font-bold");
  });

  it("renders students and building with small text", () => {
    render(<Course {...defaultProps} />);
    const students = screen.getByText("50 students");
    const building = screen.getByText("Richards Hall 101");

    expect(students.className).toContain("text-xs");
    expect(building.className).toContain("text-xs");
  });

  it("handles single digit student count", () => {
    render(<Course {...defaultProps} students="5" />);
    const students = screen.getByText("5 students");
    expect(students.textContent).toBe("5 students");
  });

  it("handles large student count", () => {
    render(<Course {...defaultProps} students="500" />);
    const students = screen.getByText("500 students");
    expect(students.textContent).toBe("500 students");
  });

  it("renders as a button element", () => {
    render(<Course {...defaultProps} />);
    const button = screen.getByRole("button");
    expect(button.tagName).toBe("BUTTON");
  });

  it("has correct structure with three text elements", () => {
    const { container } = render(<Course {...defaultProps} />);
    const spans = container.querySelectorAll("span");
    expect(spans.length).toBe(3);
  });

  it("combines custom className with default classes", () => {
    render(<Course {...defaultProps} className="my-custom-spacing" />);
    const button = screen.getByRole("button");

    expect(button.className).toContain("my-custom-spacing");
    expect(button.className).toContain("border-2");
    expect(button.className).toContain("flex-col");
  });

  it("renders all props correctly in one test", () => {
    const { container } = render(<Course {...defaultProps} />);

    expect(screen.getByText("CS 4535")).toBeDefined();
    expect(screen.getByText("50 students")).toBeDefined();
    expect(screen.getByText("Richards Hall 101")).toBeDefined();
    expect(container.querySelector("button")).toBeDefined();
  });

  it("button contains all child elements", () => {
    const { container } = render(<Course {...defaultProps} />);
    const button = container.querySelector("button");

    expect(button?.textContent).toContain("CS 4535");
    expect(button?.textContent).toContain("50 students");
    expect(button?.textContent).toContain("Richards Hall 101");
  });
});
