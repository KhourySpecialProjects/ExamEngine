import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { PersonKind, ScheduleResult } from "@/lib/api/schedules";
import { EXPLORE_KINDS, type ExploreKind } from "@/lib/scheduleView";
import { useExplorePeopleStore } from "@/lib/store/explorePeopleStore";
import { DisplaySwitch, type ExploreDisplay } from "./ExploreResults";
import { PersonExplore } from "./PersonExplore";

const KIND_LABEL: Record<ExploreKind, string> = {
  student: "Student",
  instructor: "Instructor",
};

/**
 * The Explore tab: pick what to look up (the kind is in the URL), then one
 * student or instructor, and see its exams as a calendar (default) or a list.
 */
export function ExploreView({
  scheduleId,
  schedule,
  kind,
  onKindChange,
}: {
  scheduleId: string;
  schedule: ScheduleResult;
  kind: ExploreKind;
  onKindChange: (kind: ExploreKind) => void;
}) {
  const [display, setDisplay] = useState<ExploreDisplay>("calendar");
  const pickPerson = useExplorePeopleStore((state) => state.pick);
  const explorePerson = (personKind: PersonKind, id: string) => {
    pickPerson(scheduleId, personKind, id);
    onKindChange(personKind);
  };

  return (
    <div className="space-y-3">
      <fieldset className="flex flex-wrap gap-2">
        <legend className="sr-only">Look up</legend>
        {EXPLORE_KINDS.map((k) => (
          <Button
            key={k}
            onClick={() => onKindChange(k)}
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
          <PersonExplore
            // A fresh lookup row (draft input, combobox) per kind.
            key={kind}
            scheduleId={scheduleId}
            schedule={schedule}
            kind={kind}
            display={display}
            toolbar={<DisplaySwitch display={display} onChange={setDisplay} />}
            onExplorePerson={explorePerson}
          />
        </CardContent>
      </Card>
    </div>
  );
}
