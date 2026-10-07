import { BaseAPI } from "./base";

export interface ScheduleParameters {
  student_max_per_day?: number;
  instructor_max_per_day?: number;
  avoid_back_to_back?: boolean;
  max_days?: number;
  /** Exam blocks per day: 4 (drops 7PM-9PM) or 5. */
  blocks_per_day?: 4 | 5;
  prioritize_large_courses?: boolean;
  algorithm?: "dsatur" | "annealing";
  /** Annealing search time budget in seconds. */
  time_budget_seconds?: 5 | 15 | 30;
}

/** One flat `conflicts.breakdown` record; populated fields vary by `conflict_type`. */
export interface ConflictBreakdown {
  student_id?: string | null;
  entity_id?: string | null;
  instructor_name?: string | null;
  day: string;
  block?: number;
  block_time?: string;
  conflict_type: string;
  blocks?: number[];
  block_times?: string[];
  crn?: string;
  course?: string;
  conflicting_crn?: string | null;
  conflicting_course?: string | null;
  conflicting_crns?: string[];
  conflicting_courses?: string[];
  size?: number;
}

export interface ScheduleFailure {
  CRN: string;
  Course: string;
  Size: number;
  reasons: Record<string, number>;
}

export interface ScheduleExam {
  CRN: string;
  Course: string;
  Day: string;
  Block: string;
  Room: string;
  Capacity: number;
  Size: number;
  Valid: boolean;
  Instructor?: string;
}

export interface CalendarExam {
  CRN: string;
  Course: string;
  Room: string;
  Capacity: number;
  Size: number;
  Valid: boolean;
  Instructor?: string;
}

export interface CalendarData {
  [day: string]: {
    [timeSlot: string]: CalendarExam[];
  };
}

/** An exam named in a problem list. */
export interface ExamIssue {
  crn: string;
  course: string;
  size: number;
}

export interface OverCapacityExam extends ExamIssue {
  room: string;
  capacity: number;
}

export interface GroupStats {
  groups: number;
  /** Exams (CRNs, in any state) that belong to a group. */
  sections: number;
  /** Enrollment summed over those sections. */
  students: number;
}

/** Distinct people (or exams) and how many times, as the Conflicts tab merges them. */
export interface ConflictCount {
  people: number;
  instances: number;
}

export type ConflictMetric =
  | "student_double_book"
  | "instructor_double_book"
  | "student_over_daily_limit"
  | "instructor_over_daily_limit"
  | "student_back_to_back"
  | "instructor_back_to_back"
  | "large_courses_late";

/** The settings a run used; null = not recorded by older runs. */
export interface ScheduleSettings {
  algorithm: "dsatur" | "annealing";
  blocks_per_day: number;
  time_budget_seconds: number | null;
  max_days: number | null;
  student_max_per_day: number | null;
  instructor_max_per_day: number | null;
  avoid_back_to_back: boolean | null;
  prioritize_large_courses: boolean | null;
}

export type FillBucket =
  | "under_50"
  | "from_50_to_75"
  | "from_75_to_90"
  | "from_90_to_100";

/**
 * Every number shown about one schedule, computed by the server from saved
 * rows (the browser doesn't recompute them). Field definitions: docs/DATA.md,
 * "Schedule summary".
 */
export interface ScheduleSummary {
  settings: ScheduleSettings;
  /** Settings an older run didn't record, filled with the value used then. */
  settings_assumed: (keyof ScheduleSettings)[];
  /** Recorded settings the run's algorithm ignores. */
  settings_unused: (keyof ScheduleSettings)[];
  /** From the dataset's enrollments upload; null when unknown. */
  unique_students: number | null;
  exams: {
    total: number;
    /** A day, a time and a room. */
    placed: number;
    /** No day or time. */
    unscheduled: number;
    /** A day and time but no room. */
    unroomed: number;
    over_capacity: number;
  };
  unscheduled: {
    exams: ExamIssue[];
    students: number;
    /** Groups the scheduler reported, with its reason. */
    groups: UnscheduledGroup[];
    /** Unscheduled CRNs no reported group explains (e.g. older schedules). */
    other_crns: string[];
  };
  unroomed: { exams: ExamIssue[]; students: number };
  /** Largest overflow first. */
  over_capacity: OverCapacityExam[];
  conflicts: Record<ConflictMetric, ConflictCount>;
  rooms: {
    used: number;
    /** Mean seats filled per placed exam, capped at 100% per exam (0-100). */
    average_fill: number;
    fill_buckets: Record<FillBucket, number>;
  };
  calendar: {
    /** Distinct (day, block) pairs holding an exam, unroomed included. */
    slots_used: number;
    days_used: number;
    /** Placed exams per day, Monday first. */
    days: { day: string; exams: number; seats: number }[];
    /** Placed exams per block, earliest first. */
    blocks: { label: string; exams: number }[];
    /** Placed exams per [day][block], in `days` and `blocks` order. */
    matrix: number[][];
  };
  groups: { combined: GroupStats; common: GroupStats };
  blockouts: { rooms: number; slots: number };
  /**
   * The dataset's large-only room (rooms.csv LargeOnly) and what this schedule
   * placed in it: `exams` = blocks it is used in, `sections` = CRNs seated
   * there. Null (absent on older responses) when no room is marked.
   */
  large_only_room?: {
    name: string;
    capacity: number;
    cutoff: number;
    exams: number;
    sections: number;
    students: number;
  } | null;
}

export interface ScheduleConflicts {
  total: number;
  breakdown: ConflictBreakdown[];
  details: Record<string, string[]>;
}

export interface ScheduleData {
  complete: ScheduleExam[];
  calendar: CalendarData;
  total_exams: number;
}

/**
 * An exam left entirely unscheduled, and why: a combined or common group, or a
 * single section in no group (`group` is then its CRN and `crns` just that CRN).
 */
export interface UnscheduledGroup {
  kind: "section" | "combined" | "common";
  group: string;
  reason: string;
  crns: string[];
}

/** A schedule a late-add version refers to. A deleted or unviewable one has no name. */
export interface ScheduleRef {
  id: string;
  name: string | null;
  available: boolean;
}

/** One exam added to a saved schedule by a late add (stored in the run's parameters). */
export interface LateAddition {
  crn: string;
  course_code: string;
  instructor_id: string;
  size: number;
  /** Day index, Monday = 0. */
  day: number;
  day_name: string;
  /** Block index, 0-based. */
  block: number;
  block_time: string;
  room: string;
  outcome: "clear" | "least_conflicts";
  conflicts: {
    student_double_book: number;
    student_over_daily_limit: number;
    instructor_double_book: number;
    instructor_over_daily_limit: number;
    back_to_back_students: number;
    back_to_back_instructor: number;
    large_course_late: number;
  };
  added_by: string;
  added_by_name: string;
  added_at: string;
  /** The version that added this exam. */
  schedule_id: string;
}

/** Where a schedule came from. Generated schedules: refs null, no additions. */
export interface ScheduleLineage {
  based_on: ScheduleRef | null;
  original: ScheduleRef | null;
  /** Cumulative, oldest first. */
  late_additions: LateAddition[];
  /** Viewable late-add versions based directly on this schedule, newest first. */
  newer_versions: { id: string; name: string; created_at: string }[];
}

/** What a late add needs to identify the exam (all required). */
export interface LateAddInput {
  crn: string;
  course_code: string;
  instructor_id: string;
}

/** `algorithm` of a schedule saved by a late add (`runs.algorithm_name`). */
export const LATE_ADD_ALGORITHM = "Late add";

/** `POST /schedule/{id}/late-add`: the chosen placement and the new schedule's name. */
export interface LateAddSaveBody extends LateAddInput {
  /** Day index, Monday = 0. */
  day: number;
  /** Block index, 0-based. */
  block: number;
  room: string;
  schedule_name: string;
  /** Required for a least-conflicts placement. */
  accept_conflicts: boolean;
}

export interface LateAddRoom {
  name: string;
  capacity: number;
}

/** Per-type conflict counts; student keys count distinct students, the rest are 0/1. */
export type LateAddConflictCounts = LateAddition["conflicts"];

/** A base-schedule exam; day/block/room are null when it is unscheduled. */
export interface LateAddExam {
  crn: string;
  course_code: string;
  instructor: string | null;
  size: number;
  day: number | null;
  day_name: string | null;
  block: number | null;
  block_time: string | null;
  room: string | null;
}

/** One block the late exam could go in, with who it would conflict with. */
export interface LateAddCandidate {
  /** Day index, Monday = 0. */
  day: number;
  day_name: string;
  /** Block index, 0-based. */
  block: number;
  block_time: string;
  /** Best-fit free room. */
  room: LateAddRoom;
  /** Other free rooms that fit, smallest first. */
  other_rooms: LateAddRoom[];
  clear: boolean;
  conflicts: LateAddConflictCounts;
  students: {
    /** Base CRNs the student sits in this block. */
    double_book: { student_id: string; crns: string[] }[];
    /** Exams that day including the late one. */
    over_daily_limit: { student_id: string; exams: number }[];
    /** The student's sorted blocks that day, including the late block. */
    back_to_back: {
      student_id: string;
      blocks: number[];
      block_times: string[];
    }[];
  };
  instructor: {
    double_book_crns: string[];
    /** Including the late exam. */
    exams_that_day: number;
    over_daily_limit: boolean;
    back_to_back: boolean;
    /** Empty when the instructor has no other exam that day. */
    day_blocks: number[];
    /** Labels for `day_blocks`, same order. */
    day_block_times: string[];
  };
  large_course_late: boolean;
}

/** `POST /schedule/{id}/late-add/search`. */
export interface LateAddSearchResult {
  schedule_id: string;
  crn: string;
  course_code: string;
  instructor_id: string;
  /** Distinct students enrolled on the CRN. */
  size: number;
  outcome: "clear" | "least_conflicts" | "no_room";
  settings: {
    max_days: number;
    blocks_per_day: number;
    student_max_per_day: number;
    instructor_max_per_day: number;
  };
  /** Ranked best first: only clear blocks for clear; empty for no_room. */
  candidates: LateAddCandidate[];
  /** Every block's largest free room; only filled for no_room. */
  no_room_blocks: {
    day: number;
    day_name: string;
    block: number;
    block_time: string;
    largest_free_room: LateAddRoom | null;
  }[];
  /** Base exams with this instructor: placed first, then unscheduled. */
  instructor_exams: LateAddExam[];
  /** Base exams with the same course code, same order. */
  sibling_sections: LateAddExam[];
  notes: string[];
}

/** Whose exams `GET /schedule/{id}/person-exams` looks up: an NUId or an instructor ID. */
export type PersonKind = "student" | "instructor";

/** One of a person's exams; day/block/room are null when it is unscheduled. */
export interface PersonExam {
  crn: string;
  course_code: string;
  /** Day index, Monday = 0. */
  day: number | null;
  day_name: string | null;
  /** Block index, 0-based. */
  block: number | null;
  block_time: string | null;
  /** Null when the exam has no room (unscheduled, or no room was free). */
  room: string | null;
}

/** `GET /schedule/{id}/person-exams`. */
export interface PersonExamsResult {
  kind: PersonKind;
  person_id: string;
  /** By day and block, then unscheduled exams. Empty when the ID has none. */
  exams: PersonExam[];
  /** The schedule's exam days, Monday first. */
  days: string[];
  /** The schedule's blocks per day, earliest first. */
  block_times: string[];
}

/** A (day, block) slot in which a room can't be used. */
export interface BlockedSlot {
  /** Day index, Monday = 0. */
  day: number;
  day_name: string;
  /** Block index, 0-based. */
  block: number;
  block_time: string;
}

/** `GET /schedule/{id}/rooms`: every room of the schedule's dataset. */
export interface ScheduleRoomsResult {
  /** By name; `blocked` by day and block. */
  rooms: { name: string; capacity: number; blocked: BlockedSlot[] }[];
  /**
   * "ok" when the room_blockouts file was read, "none_uploaded" when the
   * dataset has none, "unavailable" when it was deleted or can't be read.
   */
  blockouts: "ok" | "none_uploaded" | "unavailable";
  /** The schedule's exam days, Monday first. */
  days: string[];
  /** The schedule's blocks per day, earliest first. */
  block_times: string[];
}

export interface ScheduleResult {
  schedule_id: string;
  dataset_id: string;
  dataset_name: string;
  /** Detail responses only. */
  dataset_uploaded_at?: string;
  /** Detail responses only: the dataset was deleted after generation. */
  dataset_deleted?: boolean;
  schedule_name: string;
  created_at?: string;
  algorithm?: string;
  status?: "Running" | "Completed" | "Failed";
  summary: ScheduleSummary;
  conflicts: ScheduleConflicts;
  failures: ScheduleFailure[];
  schedule: ScheduleData;
  parameters: ScheduleParameters;
  /** Per-slot blocked room counts: {day_name: {block_time: n_rooms_blocked}} */
  blockouts?: Record<string, Record<string, number>>;
  /** Absent/empty for schedules generated before groups were recorded. */
  unscheduled_groups?: UnscheduledGroup[];
  is_owner?: boolean;
  is_shared?: boolean;
  created_by_user_id?: string;
  created_by_user_name?: string;
  shared_by_user_id?: string | null;
  shared_by_user_name?: string | null;
  /** Detail responses only. */
  lineage?: ScheduleLineage;
}

/** The dataset a listed schedule was generated from. */
export interface ScheduleDatasetSummary {
  name: string;
  uploaded_at: string;
  /** The dataset was deleted after the schedule was generated. */
  deleted: boolean;
  /** Null when the upload metadata has no such count. */
  courses: number | null;
  students: number | null;
  rooms: number | null;
}

export interface ScheduleListItem {
  schedule_id: string;
  schedule_name: string;
  created_at: string;
  /** The run's `algorithm_name`: the engine, or "Late add" for a late-add version. */
  algorithm: string;
  parameters: ScheduleParameters;
  status: "Running" | "Completed" | "Failed";
  dataset_id: string;
  dataset: ScheduleDatasetSummary;
  total_exams: number;
  is_shared?: boolean; // Whether this schedule is shared with the user
  is_owner?: boolean; // Whether the user owns this schedule
  created_by_user_id?: string;
  created_by_user_name?: string;
  shared_by_user_id?: string | null;
  shared_by_user_name?: string | null;
  /** Exams added by late adds (0 for generated schedules). */
  late_add_count: number;
  /** Null for generated schedules and when the base can't be viewed. */
  based_on_name: string | null;
}

export interface ScheduleShare {
  share_id: string;
  schedule_id: string;
  shared_with_user_id: string;
  shared_with_user_name: string;
  shared_with_user_email: string;
  permission: "view" | "edit";
  shared_by_user_id: string;
  shared_at: string;
}

export interface SharedSchedule {
  share_id: string;
  schedule_id: string;
  schedule_name: string;
  permission: "view" | "edit";
  shared_by_user_id: string;
  shared_by_user_name: string;
  shared_at: string;
}

/** A schedule on the Compare page, with the owner/share fields. */
export interface ComparedSchedule {
  schedule_id: string;
  status: "ok";
  schedule_name: string;
  created_at: string;
  run_status: "Running" | "Completed" | "Failed";
  dataset: {
    dataset_id: string;
    dataset_name: string;
    uploaded_at: string;
    deleted: boolean;
  };
  summary: ScheduleSummary;
  is_owner: boolean;
  is_shared: boolean;
  created_by_user_id: string;
  created_by_user_name: string;
  shared_by_user_id: string | null;
  shared_by_user_name: string | null;
}

/** Deleted, missing or not shared with the caller: nothing else is revealed. */
export interface UnavailableSchedule {
  schedule_id: string;
  status: "unavailable";
}

export type CompareItem = ComparedSchedule | UnavailableSchedule;

export class SchedulesAPI extends BaseAPI {
  async generate(
    dataset_id: string,
    schedule_name: string,
    parameters: ScheduleParameters = {},
  ): Promise<ScheduleResult> {
    const queryParams = new URLSearchParams();

    if (schedule_name) {
      queryParams.append("schedule_name", schedule_name);
    }

    if (parameters.student_max_per_day !== undefined) {
      queryParams.append(
        "student_max_per_day",
        parameters.student_max_per_day.toString(),
      );
    }
    if (parameters.instructor_max_per_day !== undefined) {
      queryParams.append(
        "instructor_max_per_day",
        parameters.instructor_max_per_day.toString(),
      );
    }
    if (parameters.avoid_back_to_back !== undefined) {
      queryParams.append(
        "avoid_back_to_back",
        parameters.avoid_back_to_back.toString(),
      );
    }
    if (parameters.max_days !== undefined) {
      queryParams.append("max_days", parameters.max_days.toString());
    }
    if (parameters.blocks_per_day !== undefined) {
      queryParams.append(
        "blocks_per_day",
        parameters.blocks_per_day.toString(),
      );
    }
    if (parameters.algorithm !== undefined) {
      queryParams.append("algorithm", parameters.algorithm);
    }
    if (parameters.time_budget_seconds !== undefined) {
      queryParams.append(
        "time_budget_seconds",
        parameters.time_budget_seconds.toString(),
      );
    }
    if (parameters.prioritize_large_courses !== undefined) {
      queryParams.append(
        "prioritize_large_courses",
        parameters.prioritize_large_courses.toString(),
      );
    }
    return this.request(
      `/schedule/generate/${dataset_id}${queryParams.toString() ? `?${queryParams}` : ""}`,
      {
        method: "POST",
      },
    );
  }
  async list(): Promise<ScheduleListItem[]> {
    return this.request("/schedule", {
      method: "GET",
    });
  }
  async get(id: string): Promise<ScheduleResult> {
    return this.request(`/schedule/${id}`, {
      method: "GET",
    });
  }

  /** Summaries of 1–4 schedules, in the given order. */
  async compare(ids: readonly string[]): Promise<{ schedules: CompareItem[] }> {
    const query = new URLSearchParams(ids.map((id) => ["ids", id]));
    return this.request(`/schedule/compare?${query}`, { method: "GET" });
  }

  async delete(id: string): Promise<{
    message: string;
    schedule_id: string;
  }> {
    return this.request(`/schedule/${id}`, {
      method: "DELETE",
    });
  }

  async shareSchedule(
    scheduleId: string,
    userId: string,
    permission: "view" | "edit",
  ): Promise<{ message: string; share_id: string }> {
    return this.request(`/schedule/${scheduleId}/share`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId, permission }),
    });
  }

  async getScheduleShares(scheduleId: string): Promise<ScheduleShare[]> {
    return this.request(`/schedule/${scheduleId}/shares`, {
      method: "GET",
    });
  }

  async unshareSchedule(shareId: string): Promise<{ message: string }> {
    return this.request(`/schedule/shares/${shareId}`, {
      method: "DELETE",
    });
  }

  async getSharedSchedules(): Promise<SharedSchedule[]> {
    return this.request("/schedule/shared", {
      method: "GET",
    });
  }

  /** Ranked blocks for an exam not in the schedule; nothing is saved. Owner only. */
  async lateAddSearch(
    scheduleId: string,
    input: LateAddInput,
  ): Promise<LateAddSearchResult> {
    return this.request(`/schedule/${scheduleId}/late-add/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    });
  }

  /** Saves a placement as a new schedule (the base is unchanged). Owner only. */
  async lateAddSave(
    scheduleId: string,
    body: LateAddSaveBody,
  ): Promise<ScheduleResult> {
    return this.request(`/schedule/${scheduleId}/late-add`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  }

  /** One student's or instructor's exams in a schedule. Owner or share recipient. */
  async personExams(
    scheduleId: string,
    kind: PersonKind,
    personId: string,
  ): Promise<PersonExamsResult> {
    const query = new URLSearchParams({ kind, person_id: personId });
    return this.request(`/schedule/${scheduleId}/person-exams?${query}`, {
      method: "GET",
    });
  }

  /** Every room with its capacity and blocked times. Owner or share recipient. */
  async rooms(scheduleId: string): Promise<ScheduleRoomsResult> {
    return this.request(`/schedule/${scheduleId}/rooms`, { method: "GET" });
  }
}
