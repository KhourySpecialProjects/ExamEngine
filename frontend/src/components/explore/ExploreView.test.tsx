import { fireEvent, render, screen, within } from "@testing-library/react";
import { useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { PersonExam, ScheduleExam } from "@/lib/api/schedules";
import type { ExploreKind } from "@/lib/scheduleView";
import { useExplorePeopleStore } from "@/lib/store/explorePeopleStore";
import { makeSchedule } from "@/test/summary";
import { ExploreView } from "./ExploreView";
import { instructorOptions } from "./PersonExplore";

vi.mock("@/lib/api/client", () => ({
  apiClient: { schedules: { personExams: vi.fn() } },
}));

import { apiClient } from "@/lib/api/client";

const personExams = vi.mocked(apiClient.schedules.personExams);

function row(
  crn: string,
  instructor: string,
  overrides: Partial<ScheduleExam> = {},
): ScheduleExam {
  return {
    CRN: crn,
    Course: `CS ${crn}`,
    Day: "Monday",
    Block: "9AM-11AM",
    Room: "Hall",
    Capacity: 40,
    Size: 30,
    Valid: true,
    Instructor: instructor,
    ...overrides,
  };
}

const ROWS = [
  row("100", "I-1"),
  row("200", " I-2 ", { Size: 12 }),
  row("300", "nan", { Day: "", Block: "", Room: "" }),
];

function exam(
  crn: string,
  day: number | null,
  block: number | null,
): PersonExam {
  return {
    crn,
    course_code: `CS ${crn}`,
    day,
    day_name: day == null ? null : ["Monday", "Tuesday"][day],
    block,
    block_time: block == null ? null : ["9AM-11AM", "11:30AM-1:30PM"][block],
    room: day == null ? null : "Hall",
  };
}

function Explore({ initialKind = "student" }: { initialKind?: ExploreKind }) {
  const [kind, setKind] = useState<ExploreKind>(initialKind);
  return (
    <ExploreView
      scheduleId="s1"
      schedule={makeSchedule({
        schedule: { complete: ROWS, calendar: {}, total_exams: ROWS.length },
      })}
      kind={kind}
      onKindChange={setKind}
    />
  );
}

function lookUpStudent(id: string) {
  fireEvent.change(screen.getByRole("textbox", { name: "NUId" }), {
    target: { value: id },
  });
  fireEvent.click(screen.getByRole("button", { name: "Look up" }));
}

const listRows = () =>
  within(screen.getByRole("table", { name: "Exams" }))
    .getAllByRole("row")
    .slice(1)
    .map((r) =>
      within(r)
        .getAllByRole("cell")
        .map((cell) => cell.textContent),
    );

describe("ExploreView", () => {
  beforeEach(() => {
    sessionStorage.clear();
    useExplorePeopleStore.setState({ people: {} });
    personExams.mockReset();
    personExams.mockImplementation(async (_s, kind, personId) => ({
      kind,
      person_id: personId,
      exams: [exam("100", 0, 0), exam("200", 0, 0), exam("300", null, null)],
      days: ["Monday", "Tuesday"],
      block_times: ["9AM-11AM", "11:30AM-1:30PM"],
    }));
  });

  it("shows a looked-up student's exams as a calendar first, then as a list", async () => {
    render(<Explore />);

    lookUpStudent(" 001234567 ");

    expect(personExams).toHaveBeenLastCalledWith("s1", "student", "001234567");
    const week = await screen.findByRole("table", { name: "Exam week" });
    expect(within(week).getByTestId("week-0-0").textContent).toBe(
      "100CS 100Hall200CS 200Hall",
    );
    expect(screen.queryByRole("table", { name: "Exams" })).toBeNull();
    expect(
      screen.getByText("1 exam unscheduled, so not on the calendar: see List."),
    ).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "List" }));

    // Instructor and size come from the schedule's rows; "nan" is no instructor.
    expect(listRows()).toEqual([
      ["Monday", "9AM-11AMDouble-booked", "100", "CS 100", "Hall", "I-1", "30"],
      ["Monday", "9AM-11AMDouble-booked", "200", "CS 200", "Hall", "I-2", "12"],
      ["Unscheduled", "—", "300", "CS 300", "—", "—", "30"],
    ]);
  });

  it("explores an instructor clicked in a student's list", async () => {
    render(<Explore />);
    lookUpStudent("001234567");
    fireEvent.click(await screen.findByRole("button", { name: "List" }));

    fireEvent.click(
      await screen.findByRole("button", { name: "Explore instructor I-2" }),
    );

    expect(personExams).toHaveBeenLastCalledWith("s1", "instructor", "I-2");
    expect(screen.getByRole("button", { name: "Instructor" }).ariaPressed).toBe(
      "true",
    );
    expect(
      screen.getByRole("combobox", { name: "Instructor" }).textContent,
    ).toBe("I-2");
    // The student is still current for the Student lookup.
    expect(useExplorePeopleStore.getState().people.s1?.student?.current).toBe(
      "001234567",
    );
  });

  it("looks a Recent student up again", async () => {
    render(<Explore />);
    lookUpStudent("001");
    lookUpStudent("002");
    await screen.findByRole("table", { name: "Exam week" });

    const recent = screen.getByText("Recent:").parentElement as HTMLElement;
    expect(
      within(recent)
        .getAllByRole("button")
        .map((b) => b.textContent),
    ).toEqual(["002", "001"]);
    fireEvent.click(within(recent).getByRole("button", { name: "001" }));

    expect(personExams).toHaveBeenLastCalledWith("s1", "student", "001");
    expect(
      (screen.getByRole("textbox", { name: "NUId" }) as HTMLInputElement).value,
    ).toBe("001");
  });

  it("restores the current student when the tab comes back", async () => {
    useExplorePeopleStore.getState().pick("s1", "student", "001234567");

    render(<Explore />);

    expect(
      await screen.findByRole("table", { name: "Exam week" }),
    ).toBeTruthy();
    expect(personExams).toHaveBeenLastCalledWith("s1", "student", "001234567");
  });
});

describe("instructorOptions", () => {
  it("lists each trimmed instructor ID once with its exam count, without 'nan'", () => {
    expect(
      instructorOptions([...ROWS, row("400", "I-1"), row("500", "")]),
    ).toEqual([
      { value: "I-1", detail: "2 exams" },
      { value: "I-2", detail: "1 exam" },
    ]);
  });
});
