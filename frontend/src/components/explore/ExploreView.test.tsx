import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type {
  PersonExam,
  ScheduleExam,
  ScheduleRoomsResult,
} from "@/lib/api/schedules";
import type { ExploreKind } from "@/lib/scheduleView";
import { useExplorePeopleStore } from "@/lib/store/explorePeopleStore";
import { makeSchedule } from "@/test/summary";
import { courseOptions } from "./CourseExplore";
import { ExploreView } from "./ExploreView";
import { instructorOptions } from "./PersonExplore";

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    schedules: { personExams: vi.fn(), rooms: vi.fn() },
    datasets: { getCourseMerges: vi.fn(), getCommonExams: vi.fn() },
  },
}));

import { apiClient } from "@/lib/api/client";

const personExams = vi.mocked(apiClient.schedules.personExams);
const rooms = vi.mocked(apiClient.schedules.rooms);
const getCourseMerges = vi.mocked(apiClient.datasets.getCourseMerges);
const getCommonExams = vi.mocked(apiClient.datasets.getCommonExams);

const DAYS = ["Monday", "Tuesday"];
const TIMES = ["8AM-10AM", "10:30AM-12:30PM"];

/** Hall is blocked on Monday 8AM (where its two exams are) and Tuesday 10:30AM. */
function roomsResult(
  blockouts: ScheduleRoomsResult["blockouts"] = "ok",
): ScheduleRoomsResult {
  return {
    rooms: [
      { name: "Empty", capacity: 10, blocked: [] },
      {
        name: "Hall",
        capacity: 40,
        blocked:
          blockouts === "ok"
            ? [
                { day: 0, day_name: DAYS[0], block: 0, block_time: TIMES[0] },
                { day: 1, day_name: DAYS[1], block: 1, block_time: TIMES[1] },
              ]
            : [],
      },
      { name: "Lab", capacity: 30, blocked: [] },
    ],
    blockouts,
    days: DAYS,
    block_times: TIMES,
  };
}

function row(
  crn: string,
  instructor: string,
  overrides: Partial<ScheduleExam> = {},
): ScheduleExam {
  return {
    CRN: crn,
    Course: `CS ${crn}`,
    Day: "Monday",
    Block: "8AM-10AM",
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
    day_name: day == null ? null : DAYS[day],
    block,
    block_time: block == null ? null : TIMES[block],
    room: day == null ? null : "Hall",
  };
}

function Explore({
  initialKind = "student",
  initialQuery = null,
  rows = ROWS,
}: {
  initialKind?: ExploreKind;
  initialQuery?: string | null;
  rows?: ScheduleExam[];
}) {
  const [lookup, setLookup] = useState({
    kind: initialKind,
    query: initialQuery,
  });
  return (
    <ExploreView
      scheduleId="s1"
      schedule={makeSchedule({
        schedule: { complete: rows, calendar: {}, total_exams: rows.length },
      })}
      kind={lookup.kind}
      query={lookup.query}
      onLookupChange={(kind, query) => setLookup({ kind, query })}
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
    rooms.mockReset();
    rooms.mockResolvedValue(roomsResult());
    getCourseMerges.mockReset();
    getCourseMerges.mockResolvedValue({});
    getCommonExams.mockReset();
    getCommonExams.mockResolvedValue({});
    personExams.mockImplementation(async (_s, kind, personId) => ({
      kind,
      person_id: personId,
      exams: [exam("100", 0, 0), exam("200", 0, 0), exam("300", null, null)],
      days: DAYS,
      block_times: TIMES,
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
      [
        "Monday",
        "8AM-10AMDouble-booked",
        "100",
        "CS 100",
        "Hall",
        "I-1",
        "30",
        "—",
      ],
      [
        "Monday",
        "8AM-10AMDouble-booked",
        "200",
        "CS 200",
        "Hall",
        "I-2",
        "12",
        "—",
      ],
      ["Unscheduled", "—", "300", "CS 300", "—", "—", "30", "—"],
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

  it("shows a room's exams and blocked slots, flagging exams inside one", async () => {
    render(<Explore initialKind="room" initialQuery="Hall" />);

    const week = await screen.findByRole("table", { name: "Exam week" });
    expect(rooms).toHaveBeenCalledWith("s1");
    expect(screen.getByRole("heading").textContent).toBe(
      "Room Hall(capacity 40)",
    );
    const blockedWithExams = within(week).getByTestId("week-0-0");
    expect(blockedWithExams.textContent).toBe(
      "Blocked100CS 100Hall200CS 200Hall",
    );
    const blocks = blockedWithExams.querySelectorAll("[title^='CRN']");
    expect(blocks).toHaveLength(2);
    for (const block of blocks) {
      expect(block.getAttribute("title")).toContain("in a blocked slot");
    }
    expect(within(week).getByTestId("week-1-1").textContent).toBe("Blocked");
    expect(within(week).getByTestId("week-1-0").textContent).toBe("");
    expect(
      within(screen.getByRole("list", { name: "Legend" }))
        .getAllByRole("listitem")
        .map((li) => li.textContent),
    ).toEqual([
      "Exam",
      "Blocked (room not available)",
      "Exam in a blocked slot",
    ]);

    fireEvent.click(screen.getByRole("button", { name: "List" }));

    // No Room column, no double-book marks: a room holds combined exams.
    expect(listRows()).toEqual([
      ["Monday", "8AM-10AMBlocked slot", "100", "CS 100", "I-1", "30", "—"],
      ["Monday", "8AM-10AMBlocked slot", "200", "CS 200", "I-2", "12", "—"],
    ]);
    const blockedTimes = screen.getByText("Blocked times (2)")
      .parentElement as HTMLDetailsElement;
    expect(blockedTimes.open).toBe(false);
    expect(
      within(blockedTimes)
        .getAllByRole("listitem", { hidden: true })
        .map((li) => li.textContent),
    ).toEqual(["Monday 8AM-10AM", "Tuesday 10:30AM-12:30PM"]);
  });

  it("picks a room from the list of every room", async () => {
    // cmdk measures its list and scrolls the active item into view.
    global.ResizeObserver ??= class {
      observe() {}
      unobserve() {}
      disconnect() {}
    };
    Element.prototype.scrollIntoView ??= () => {};
    render(<Explore initialKind="room" />);
    fireEvent.click(await screen.findByRole("combobox", { name: "Room" }));

    const options = await screen.findAllByRole("option");
    expect(options.map((o) => o.textContent)).toEqual([
      "Emptycapacity 10 · 0 exams",
      "Hallcapacity 40 · 2 exams",
      "Labcapacity 30 · 0 exams",
    ]);
    fireEvent.click(options[0]);

    expect(
      await screen.findByText("No exams in this room in this schedule."),
    ).toBeTruthy();
    expect(screen.getByText("0 exams, 0 blocked slots")).toBeTruthy();
  });

  it("says when the room's blocked times can't be read", async () => {
    rooms.mockResolvedValue(roomsResult("unavailable"));
    render(<Explore initialKind="room" initialQuery="Hall" />);

    expect(
      await screen.findByText(
        "Blocked times are unavailable: the dataset's room blockouts file can't be read.",
      ),
    ).toBeTruthy();
    expect(screen.getByTestId("week-0-0").textContent).toBe(
      "100CS 100Hall200CS 200Hall",
    );
  });

  it("explores a room clicked in a student's calendar", async () => {
    render(<Explore />);
    lookUpStudent("001234567");
    expect(rooms).not.toHaveBeenCalled();

    fireEvent.click(
      (await screen.findAllByRole("button", { name: "Explore room Hall" }))[0],
    );

    expect(screen.getByRole("button", { name: "Room" }).ariaPressed).toBe(
      "true",
    );
    expect((await screen.findByRole("heading")).textContent).toBe(
      "Room Hall(capacity 40)",
    );
  });

  describe("course lookup", () => {
    const SECTIONS = [
      row("100", "I-1"),
      row("101", "I-2", { Course: "CS 100", Day: "Tuesday", Block: TIMES[1] }),
      row("200", "I-2", { Room: "Lab" }),
    ];

    it("shows every section of a course code", async () => {
      render(
        <Explore initialKind="course" initialQuery="CS 100" rows={SECTIONS} />,
      );

      const week = await screen.findByRole("table", { name: "Exam week" });
      expect(screen.getByRole("heading").textContent).toBe("Course CS 100");
      expect(within(week).getByTestId("week-0-0").textContent).toBe(
        "100CS 100Hall",
      );
      expect(within(week).getByTestId("week-1-1").textContent).toBe(
        "101CS 100Hall",
      );
      // Same-course sections may share a block: never a double-book.
      expect(screen.queryByRole("list", { name: "Legend" })).toBeNull();

      fireEvent.click(screen.getByRole("button", { name: "List" }));
      expect(listRows()).toEqual([
        ["Monday", "8AM-10AM", "100", "CS 100", "Hall", "I-1", "30", "—"],
        [
          "Tuesday",
          "10:30AM-12:30PM",
          "101",
          "CS 100",
          "Hall",
          "I-2",
          "30",
          "—",
        ],
      ]);
    });

    it("shows one exam for a CRN", async () => {
      render(
        <Explore initialKind="course" initialQuery="200" rows={SECTIONS} />,
      );

      await screen.findByRole("table", { name: "Exam week" });
      expect(screen.getByRole("heading").textContent).toBe("CRN 200· CS 200");
      expect(screen.getByTestId("week-0-0").textContent).toBe("200CS 200Lab");
    });

    it("lists course codes with their sections, then CRNs", () => {
      expect(courseOptions(SECTIONS)).toEqual([
        { value: "CS 100", detail: "2 sections" },
        { value: "CS 200", detail: "1 section" },
        { value: "100", detail: "CS 100" },
        { value: "101", detail: "CS 100" },
        { value: "200", detail: "CS 200" },
      ]);
    });
  });

  describe("combined and common exams", () => {
    // 100 + 200 are one combined exam in Hall; it belongs to a common exam
    // with 900 in Lab, all Monday 8AM.
    const GROUP_ROWS = [
      row("100", "I-1"),
      row("200", "I-1", { Size: 12 }),
      row("900", "I-9", { Room: "Lab" }),
    ];
    beforeEach(() => {
      getCourseMerges.mockResolvedValue({ "CS Combined": ["100", "200"] });
      getCommonExams.mockResolvedValue({ "CS Common": ["100", "900"] });
    });

    it("frames a room's combined exam and lists its common exam's sections", async () => {
      render(
        <Explore initialKind="room" initialQuery="Hall" rows={GROUP_ROWS} />,
      );

      const frame = await screen.findByTestId("combined-exam");
      expect(getCourseMerges).toHaveBeenCalledWith("d1");
      expect(frame.textContent).toBe(
        "CS CombinedHall · 42 students100 CS 100200 CS 200",
      );
      expect(
        within(screen.getByRole("list", { name: "Legend" }))
          .getAllByRole("listitem")
          .map((li) => li.textContent),
      ).toContain("Combined exam (sections share a room)");

      fireEvent.click(
        within(frame).getByRole("button", {
          name: "Common exam CS Common: show its sections",
        }),
      );
      const sections = await screen.findByRole("list", {
        name: "Sections of CS Common",
      });
      expect(
        within(sections)
          .getAllByRole("listitem")
          .map((li) => li.textContent),
      ).toEqual(["100CS 100Hall", "200CS 200Hall", "900CS 900Lab"]);

      fireEvent.click(
        within(sections).getByRole("button", { name: "Explore room Lab" }),
      );
      expect((await screen.findByRole("heading")).textContent).toBe(
        "Room Lab(capacity 30)",
      );
    });

    it("does not call sections of one combined exam a double-book", async () => {
      render(<Explore rows={GROUP_ROWS} />);
      await waitFor(() => expect(getCommonExams).toHaveBeenCalled());

      lookUpStudent("001234567");
      fireEvent.click(await screen.findByRole("button", { name: "List" }));

      // 100 and 200 share Monday 8AM but are one exam; 300 is unscheduled.
      await waitFor(() =>
        expect(listRows()[0][7]).toBe("CS CombinedCS Common"),
      );
      expect(screen.queryByText("Double-booked")).toBeNull();
    });
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
