import { beforeEach, describe, expect, it } from "vitest";
import { RECENT_PEOPLE, useExplorePeopleStore } from "./explorePeopleStore";

const KEY = "explore-people-storage";
const pickOf = (scheduleId: string, kind: "student" | "instructor") =>
  useExplorePeopleStore.getState().people[scheduleId]?.[kind];

describe("explorePeopleStore", () => {
  beforeEach(() => {
    sessionStorage.clear();
    useExplorePeopleStore.setState({ people: {} });
  });

  it("makes a pick current and keeps Recent newest first without repeats", () => {
    const { pick } = useExplorePeopleStore.getState();
    pick("s1", "student", "A");
    pick("s1", "student", "B");
    pick("s1", "student", "A");

    expect(pickOf("s1", "student")).toEqual({
      current: "A",
      recent: ["A", "B"],
    });
  });

  it("keeps picks apart per schedule and per kind, and caps Recent", () => {
    const { pick } = useExplorePeopleStore.getState();
    for (let i = 0; i < RECENT_PEOPLE + 2; i++) pick("s1", "student", `S${i}`);
    pick("s1", "instructor", "I-1");
    pick("s2", "student", "X");

    expect(pickOf("s1", "student")?.recent).toEqual([
      "S6",
      "S5",
      "S4",
      "S3",
      "S2",
    ]);
    expect(pickOf("s1", "instructor")?.current).toBe("I-1");
    expect(pickOf("s2", "student")?.recent).toEqual(["X"]);
  });

  it("is saved to sessionStorage and restores only well-formed picks", async () => {
    useExplorePeopleStore.getState().pick("s1", "student", "A");
    expect(JSON.parse(sessionStorage.getItem(KEY) ?? "{}").state).toEqual({
      people: { s1: { student: { current: "A", recent: ["A"] } } },
    });

    // Setting state saves it, so empty the store before planting storage.
    useExplorePeopleStore.setState({ people: {} });
    sessionStorage.setItem(
      KEY,
      JSON.stringify({
        state: {
          people: {
            s1: {
              student: { current: "B", recent: ["B", "A"] },
              instructor: { current: 7, recent: [] },
            },
            s2: "junk",
          },
        },
        version: 0,
      }),
    );
    await useExplorePeopleStore.persist.rehydrate();

    expect(useExplorePeopleStore.getState().people).toEqual({
      s1: { student: { current: "B", recent: ["B", "A"] } },
      s2: {},
    });
  });
});
