import { describe, expect, it } from "vitest";
import type { ScheduleListItem } from "@/lib/api/schedules";
import { groupSchedulesByDataset, type ScheduleGroup } from "./scheduleGroups";

const schedule = (
  name: string,
  createdAt: string,
  dataset: string,
  { uploaded = "2026-01-01T00:00:00", exams = 10 } = {},
): ScheduleListItem => ({
  schedule_id: name,
  schedule_name: name,
  created_at: createdAt,
  algorithm: "DSATUR",
  parameters: {},
  status: "Completed",
  dataset_id: dataset,
  dataset: {
    name: dataset,
    uploaded_at: uploaded,
    deleted: false,
    courses: 1,
    students: 1,
    rooms: 1,
  },
  total_exams: exams,
  late_add_count: 0,
  based_on_name: null,
});

const SCHEDULES = [
  schedule("Spring A", "2026-03-01T09:00:00", "Spring", {
    uploaded: "2026-02-01T00:00:00",
    exams: 5,
  }),
  schedule("Autumn A", "2026-01-10T09:00:00", "Autumn", {
    uploaded: "2026-03-01T00:00:00",
  }),
  schedule("Spring B", "2026-03-05T09:00:00", "Spring", {
    uploaded: "2026-02-01T00:00:00",
    exams: 50,
  }),
  schedule("Autumn B", "2026-04-01T09:00:00", "Autumn", {
    uploaded: "2026-03-01T00:00:00",
  }),
];

const shape = (groups: ScheduleGroup[]) =>
  groups.map((g) => [g.dataset.name, g.schedules.map((s) => s.schedule_name)]);

describe("groupSchedulesByDataset", () => {
  it("defaults to latest run first, newest schedule first within each dataset", () => {
    const groups = groupSchedulesByDataset(SCHEDULES, {});

    expect(shape(groups)).toEqual([
      ["Autumn", ["Autumn B", "Autumn A"]],
      ["Spring", ["Spring B", "Spring A"]],
    ]);
    expect(groups[0].latestRun).toBe("2026-04-01T09:00:00");
  });

  it("orders groups by name or upload date and schedules by the chosen key", () => {
    expect(
      shape(
        groupSchedulesByDataset(SCHEDULES, {
          groupSort: "name",
          scheduleSort: "oldest",
        }),
      ),
    ).toEqual([
      ["Autumn", ["Autumn A", "Autumn B"]],
      ["Spring", ["Spring A", "Spring B"]],
    ]);
    expect(
      shape(
        groupSchedulesByDataset(SCHEDULES, {
          groupSort: "uploaded",
          scheduleSort: "exams",
        }),
      ),
    ).toEqual([
      ["Autumn", ["Autumn A", "Autumn B"]],
      ["Spring", ["Spring B", "Spring A"]],
    ]);
  });

  it("keeps a whole dataset when its name matches, else only matching schedules", () => {
    expect(
      shape(groupSchedulesByDataset(SCHEDULES, { search: "spring" })),
    ).toEqual([["Spring", ["Spring B", "Spring A"]]]);
    expect(
      shape(groupSchedulesByDataset(SCHEDULES, { search: " b " })),
    ).toEqual([
      ["Autumn", ["Autumn B"]],
      ["Spring", ["Spring B"]],
    ]);
    expect(groupSchedulesByDataset(SCHEDULES, { search: "winter" })).toEqual(
      [],
    );
  });
});
