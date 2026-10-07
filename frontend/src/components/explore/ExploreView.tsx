import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { PersonKind, ScheduleResult } from "@/lib/api/schedules";
import { useScheduleRooms } from "@/lib/hooks/useScheduleRooms";
import { EXPLORE_KINDS, type ExploreKind } from "@/lib/scheduleView";
import { useExplorePeopleStore } from "@/lib/store/explorePeopleStore";
import { CourseExplore } from "./CourseExplore";
import { DisplaySwitch, type ExploreDisplay } from "./ExploreResults";
import { PersonExplore } from "./PersonExplore";
import { RoomExplore } from "./RoomExplore";

const KIND_LABEL: Record<ExploreKind, string> = {
  room: "Room",
  student: "Student",
  instructor: "Instructor",
  course: "Course",
};

/**
 * The Explore tab: pick what to look up, then one room, student, instructor
 * or course, and see its exams as a calendar (default) or a list. The kind
 * and a room or course (`query`) are in the URL; people are in
 * `explorePeopleStore`.
 */
export function ExploreView({
  scheduleId,
  schedule,
  kind,
  query,
  onLookupChange,
}: {
  scheduleId: string;
  schedule: ScheduleResult;
  kind: ExploreKind;
  /** The room, CRN or course code looked up; null for people. */
  query: string | null;
  onLookupChange: (kind: ExploreKind, query: string | null) => void;
}) {
  const [display, setDisplay] = useState<ExploreDisplay>("calendar");
  // Rooms and courses draw the week the rooms reply describes.
  const rooms = useScheduleRooms(
    scheduleId,
    kind === "room" || kind === "course",
  );
  const pickPerson = useExplorePeopleStore((state) => state.pick);
  const explorePerson = (personKind: PersonKind, id: string) => {
    pickPerson(scheduleId, personKind, id);
    onLookupChange(personKind, null);
  };
  const exploreRoom = (room: string) => onLookupChange("room", room);
  const toolbar = <DisplaySwitch display={display} onChange={setDisplay} />;

  return (
    <div className="space-y-3">
      <fieldset className="flex flex-wrap gap-2">
        <legend className="sr-only">Look up</legend>
        {EXPLORE_KINDS.map((k) => (
          <Button
            key={k}
            onClick={() => onLookupChange(k, null)}
            aria-pressed={kind === k}
            className={`rounded-md px-3 py-1 text-sm font-medium transition-colors ${
              kind === k
                ? "bg-primary text-primary-foreground"
                : "bg-muted text-muted-foreground hover:bg-muted/80"
            }`}
          >
            {KIND_LABEL[k]}
          </Button>
        ))}
      </fieldset>
      <Card>
        <CardContent>
          {kind === "room" ? (
            <RoomExplore
              schedule={schedule}
              room={query}
              rooms={rooms}
              display={display}
              toolbar={toolbar}
              onRoomChange={exploreRoom}
              onInstructorClick={(id) => explorePerson("instructor", id)}
            />
          ) : kind === "course" ? (
            <CourseExplore
              schedule={schedule}
              course={query}
              rooms={rooms}
              display={display}
              toolbar={toolbar}
              onCourseChange={(course) => onLookupChange("course", course)}
              onInstructorClick={(id) => explorePerson("instructor", id)}
              onRoomClick={exploreRoom}
            />
          ) : (
            <PersonExplore
              // A fresh lookup row (draft input, combobox) per kind.
              key={kind}
              scheduleId={scheduleId}
              schedule={schedule}
              kind={kind}
              display={display}
              toolbar={toolbar}
              onExplorePerson={explorePerson}
              onRoomClick={exploreRoom}
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
