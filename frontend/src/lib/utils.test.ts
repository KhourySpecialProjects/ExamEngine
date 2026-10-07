import { describe, expect, it } from "vitest";
import { scheduleExportRows } from "./utils";

const row = (Block: string) => ({
  CRN: "100",
  Course: "TEST 100",
  Day: "Monday",
  Block,
  Room: "Hall A",
});

describe("scheduleExportRows", () => {
  it("replaces Block with 24-hour start and end columns in its place", () => {
    const rows = scheduleExportRows([
      row("8AM-10AM"),
      row("10:30AM-12:30PM"),
      row("1PM-3PM"),
      row("3:30PM-5:30PM"),
      row("6PM-8PM"),
    ]);

    expect(Object.keys(rows[0])).toEqual([
      "CRN",
      "Course",
      "Day",
      "Start Time",
      "End Time",
      "Room",
    ]);
    expect(rows.map((r) => [r["Start Time"], r["End Time"]])).toEqual([
      ["08:00", "10:00"],
      ["10:30", "12:30"],
      ["13:00", "15:00"],
      ["15:30", "17:30"],
      ["18:00", "20:00"],
    ]);
  });

  it("leaves both times blank for an unscheduled exam", () => {
    const [unscheduled] = scheduleExportRows([{ ...row(""), Day: "" }]);

    expect(unscheduled["Start Time"]).toBe("");
    expect(unscheduled["End Time"]).toBe("");
    expect(unscheduled).not.toHaveProperty("Block");
  });
});
