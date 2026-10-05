import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { PersonExam, PersonExamsResult } from "@/lib/api/schedules";
import { PersonExams } from "./PersonExams";
import { PersonIdActions } from "./PersonIdActions";

vi.mock("@/lib/api/client", () => ({
  apiClient: { schedules: { personExams: vi.fn() } },
}));

import { apiClient } from "@/lib/api/client";

const personExams = vi.mocked(apiClient.schedules.personExams);

const DAYS = ["Monday", "Tuesday", "Wednesday"];
const TIMES = ["9AM-11AM", "11:30AM-1:30PM", "2PM-4PM"];

function exam(
  crn: string,
  day: number | null,
  block: number | null,
  room: string | null = "Hall",
): PersonExam {
  return {
    crn,
    course_code: `CS ${crn}`,
    day,
    day_name: day === null ? null : DAYS[day],
    block,
    block_time: block === null ? null : TIMES[block],
    room: day === null ? null : room,
  };
}

function result(exams: PersonExam[]): PersonExamsResult {
  return {
    kind: "student",
    person_id: "001234567",
    exams,
    days: DAYS,
    block_times: TIMES,
  };
}

const listRows = () =>
  within(screen.getByRole("table", { name: "Exams" }))
    .getAllByRole("row")
    .slice(1)
    .map((row) =>
      within(row)
        .getAllByRole("cell")
        .map((cell) => cell.textContent),
    );

const weekCell = (day: number, block: number) =>
  screen.getByTestId(`week-${day}-${block}`);

describe("PersonExams", () => {
  it("lists exams in week order with unscheduled last and blocks each one out", () => {
    render(
      <PersonExams
        result={result([
          exam("100", 0, 0),
          exam("300", 2, 1, null),
          exam("400", null, null),
        ])}
      />,
    );

    expect(listRows()).toEqual([
      ["Monday", "9AM-11AM", "100", "CS 100", "Hall"],
      ["Wednesday", "11:30AM-1:30PM", "300", "CS 300", "No room"],
      ["Unscheduled", "—", "400", "CS 400", "—"],
    ]);
    expect(
      within(screen.getByRole("table", { name: "Exam week" }))
        .getAllByRole("columnheader")
        .map((th) => th.textContent),
    ).toEqual(["", ...DAYS]);
    expect(weekCell(0, 0).textContent).toBe("100CS 100Hall");
    expect(weekCell(2, 1).textContent).toBe("300CS 300No room");
    expect(weekCell(1, 0).textContent).toBe("");
    expect(screen.queryByText("Double-booked")).toBeNull();
  });

  it("marks exams that share a block as double-booked, in red", () => {
    render(
      <PersonExams
        result={result([
          exam("100", 0, 0),
          exam("200", 0, 0),
          exam("300", 1, 0),
        ])}
      />,
    );

    expect(screen.getAllByText("Double-booked")).toHaveLength(2);
    const blocks = weekCell(0, 0).querySelectorAll("[title]");
    expect(blocks).toHaveLength(2);
    for (const block of blocks) {
      expect(block.className).toContain("border-destructive");
    }
    expect(weekCell(1, 0).querySelector("[title]")?.className).not.toContain(
      "border-destructive",
    );
  });

  it("draws a proposed late add dashed, and a clash with it is a double-book", () => {
    render(
      <PersonExams
        result={result([exam("100", 0, 1)])}
        proposed={{ ...exam("900", 0, 1), room: "Lab" }}
      />,
    );

    expect(listRows()[1]).toEqual([
      "Monday",
      "11:30AM-1:30PMDouble-booked",
      "900Proposed",
      "CS 900",
      "Lab",
    ]);
    const [base, late] = weekCell(0, 1).querySelectorAll("[title]");
    expect(base.textContent).toBe("100CS 100Hall");
    expect(late.textContent).toBe("900CS 900LabProposed");
    expect(late.className).toContain("border-dashed");
    expect(late.className).toContain("border-destructive");
  });

  it("says so when the person has no exams", () => {
    render(<PersonExams result={result([])} />);

    expect(
      screen.getByText("No exams for this student in this schedule."),
    ).toBeTruthy();
    expect(screen.queryByRole("table")).toBeNull();
  });
});

describe("PersonIdActions", () => {
  it("opens the person's exams in the given schedule", async () => {
    personExams.mockResolvedValue(result([exam("100", 0, 0)]));
    render(<PersonIdActions id="001234567" kind="student" scheduleId="s1" />);

    fireEvent.click(
      screen.getByRole("button", { name: "View exams for NUId 001234567" }),
    );

    const dialog = await screen.findByRole("dialog");
    expect(personExams).toHaveBeenLastCalledWith("s1", "student", "001234567");
    expect(within(dialog).getByText("Exams for NUId 001234567")).toBeTruthy();
    expect(
      await within(dialog).findByText("CS 100", { selector: "td" }),
    ).toBeTruthy();
  });

  it("shows why the exams couldn't be loaded", async () => {
    personExams.mockRejectedValue(new Error("Could not read the file."));
    render(<PersonIdActions id="I-1" kind="instructor" scheduleId="s1" />);

    fireEvent.click(
      screen.getByRole("button", { name: "View exams for instructor I-1" }),
    );

    expect((await screen.findByRole("alert")).textContent).toBe(
      "Could not read the file.",
    );
  });

  it("only copies a 'nan' ID or one outside a schedule", () => {
    render(
      <>
        <PersonIdActions id="nan" kind="instructor" scheduleId="s1" />
        <PersonIdActions id="I-2" kind="instructor" scheduleId={undefined} />
      </>,
    );

    expect(screen.getAllByRole("button").map((b) => b.ariaLabel)).toEqual([
      "Copy instructor nan",
      "Copy instructor I-2",
    ]);
  });
});
