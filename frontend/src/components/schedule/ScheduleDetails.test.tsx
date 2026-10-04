import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { makeLateAddition, makeSchedule } from "@/test/summary";
import { ScheduleDetails } from "./ScheduleDetails";

describe("ScheduleDetails lineage", () => {
  it("links the base and shows an unavailable original, with every late addition", () => {
    render(
      <ScheduleDetails
        schedule={makeSchedule({
          schedule_id: "s3",
          schedule_name: "Fall + 2",
          algorithm: "Late add",
          lineage: {
            based_on: { id: "s2", name: "Fall + 1", available: true },
            // The original was deleted.
            original: { id: "s1", name: null, available: false },
            late_additions: [
              makeLateAddition(),
              makeLateAddition({
                crn: "90002",
                course_code: "MATH 2000",
                instructor_id: "I-9",
                day_name: "Tuesday",
                block_time: "2PM-4PM",
                room: "Room 7",
                outcome: "least_conflicts",
                conflicts: {
                  ...makeLateAddition().conflicts,
                  student_double_book: 2,
                },
                added_by_name: "Bo",
                schedule_id: "s3",
              }),
            ],
            newer_versions: [],
          },
        })}
      />,
    );

    expect(
      screen.getByRole("link", { name: "Fall + 1" }).getAttribute("href"),
    ).toBe("/dashboard/s2");
    expect(screen.getByText("Original:").nextElementSibling?.textContent).toBe(
      "Not available",
    );
    expect(screen.getByText("Saved")).toBeTruthy();

    const rows = within(
      screen.getByRole("table", { name: "Late additions" }),
    ).getAllByRole("row");
    expect(
      rows.map((row) =>
        within(row)
          .queryAllByRole("cell")
          .map((cell) => cell.textContent),
      ),
    ).toEqual([
      [],
      [
        "90001",
        "CS 1000",
        "I-1",
        "Monday 9AM-11AM",
        "Hall A",
        "Clear",
        expect.stringMatching(/^Ada.*2026/),
      ],
      [
        "90002",
        "MATH 2000",
        "I-9",
        "Tuesday 2PM-4PM",
        "Room 7",
        "Least conflicts2 students double-booked",
        expect.stringMatching(/^Bo.*2026/),
      ],
    ]);
  });

  it("shows no lineage for a generated schedule", () => {
    render(<ScheduleDetails schedule={makeSchedule()} />);

    expect(screen.queryByText("Late add to")).toBeNull();
    expect(screen.queryByRole("table")).toBeNull();
    expect(screen.getByText("Generated")).toBeTruthy();
  });
});
