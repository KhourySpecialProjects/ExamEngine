/**
 * The schedule page's view, conflict type and Explore lookup, kept in the URL
 * (`/dashboard/<id>?view=conflicts&type=student_double_book`,
 * `?view=explore&kind=room&q=<room>`) so other pages can link straight to
 * them. Student and instructor IDs are never put in the URL: Explore keeps
 * them in sessionStorage (`lib/store/explorePeopleStore`).
 */
import { createSerializer, parseAsString, parseAsStringLiteral } from "nuqs";

export const SCHEDULE_VIEWS = [
  "density",
  "compact",
  "list",
  "statistics",
  "conflicts",
  "explore",
] as const;

export type ScheduleView = (typeof SCHEDULE_VIEWS)[number];

/** What the Explore tab looks up, in the order its picker lists them. */
export const EXPLORE_KINDS = ["room", "student", "instructor"] as const;

export type ExploreKind = (typeof EXPLORE_KINDS)[number];

/** Unknown values read as the default view and the first conflict type. */
export const scheduleViewParams = {
  view: parseAsStringLiteral(SCHEDULE_VIEWS).withDefault("density"),
  /** A conflict breakdown type, e.g. `student_double_book`. */
  type: parseAsString,
  /** Explore: what is looked up. */
  kind: parseAsStringLiteral(EXPLORE_KINDS).withDefault("room"),
  /** Explore: the room looked up (never a person's ID). */
  q: parseAsString,
};

const serialize = createSerializer(scheduleViewParams);

/** Link to a schedule, optionally on a view, conflict type or Explore lookup. */
export function scheduleHref(
  scheduleId: string,
  params: {
    view?: ScheduleView;
    type?: string;
    kind?: ExploreKind;
    q?: string;
  } = {},
): string {
  return serialize(`/dashboard/${scheduleId}`, params);
}
