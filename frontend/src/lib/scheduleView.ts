/**
 * The schedule page's view and conflict type, kept in the URL
 * (`/dashboard/<id>?view=conflicts&type=student_double_book`) so other pages
 * can link straight to them.
 */
import { createSerializer, parseAsString, parseAsStringLiteral } from "nuqs";

export const SCHEDULE_VIEWS = [
  "density",
  "compact",
  "list",
  "statistics",
  "conflicts",
] as const;

export type ScheduleView = (typeof SCHEDULE_VIEWS)[number];

/** Unknown values read as the default view and the first conflict type. */
export const scheduleViewParams = {
  view: parseAsStringLiteral(SCHEDULE_VIEWS).withDefault("density"),
  /** A conflict breakdown type, e.g. `student_double_book`. */
  type: parseAsString,
};

const serialize = createSerializer(scheduleViewParams);

/** Link to a schedule, optionally on a view and conflict type. */
export function scheduleHref(
  scheduleId: string,
  params: { view?: ScheduleView; type?: string } = {},
): string {
  return serialize(`/dashboard/${scheduleId}`, params);
}
