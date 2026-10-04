import {
  Ban,
  BookOpen,
  Building2,
  Clock,
  GitMerge,
  Layers,
  Users,
} from "lucide-react";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useSchedulesStore } from "@/lib/store/schedulesStore";
import { DistributionCharts } from "./DistributionCharts";
import { ProblemsSection } from "./ProblemsSection";
import { StatCard, StatGroupCard } from "./StatCard";

/**
 * Statistics tab: problems first, then the overview, exam groups and room
 * constraints, then how exams are spread over the exam period.
 */
export function StatisticsView({
  onShowConflicts,
}: {
  /** Switches the schedule page to the Conflicts tab. */
  onShowConflicts?: () => void;
}) {
  const summary = useSchedulesStore(
    (state) => state.currentSchedule?.summary ?? null,
  );

  if (!summary) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Statistics Dashboard</CardTitle>
          <CardDescription>
            Generate a schedule to view statistics
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const { exams, groups, blockouts } = summary;
  const placedPercent =
    exams.total > 0 ? Math.round((exams.placed / exams.total) * 1000) / 10 : 0;
  const groupCards = [
    groups.combined.groups > 0 && (
      <StatGroupCard
        key="combined"
        title="Combined exams"
        icon={GitMerge}
        items={[
          { label: "Groups", value: groups.combined.groups },
          { label: "Sections", value: groups.combined.sections },
          { label: "Students", value: groups.combined.students },
        ]}
      />
    ),
    groups.common.groups > 0 && (
      <StatGroupCard
        key="common"
        title="Common exams"
        icon={Layers}
        items={[
          { label: "Groups", value: groups.common.groups },
          { label: "Sections", value: groups.common.sections },
          { label: "Students", value: groups.common.students },
        ]}
      />
    ),
    blockouts.rooms > 0 && (
      <StatGroupCard
        key="blockouts"
        title="Room blockouts"
        icon={Ban}
        items={[
          { label: "Rooms blocked", value: blockouts.rooms },
          { label: "Blocked slots", value: blockouts.slots },
        ]}
      />
    ),
  ].filter(Boolean);

  return (
    <div className="space-y-6">
      <div className="pl-2">
        <h1 className="text-2xl font-bold">Statistics View</h1>
        <p className="text-muted-foreground">
          Analytics and insights about your exam schedule
        </p>
      </div>

      <ProblemsSection summary={summary} onShowConflicts={onShowConflicts} />

      <section aria-labelledby="stats-overview" className="space-y-3">
        <h2 id="stats-overview" className="pl-2 text-lg font-semibold">
          Overview
        </h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <StatCard
            title="Exams scheduled"
            icon={BookOpen}
            value={`${exams.placed.toLocaleString()} / ${exams.total.toLocaleString()}`}
            detail={`${placedPercent}% have a day, time and room`}
          />
          <StatCard
            title="Students"
            icon={Users}
            value={summary.unique_students?.toLocaleString() ?? "—"}
            detail={
              summary.unique_students == null
                ? "Dataset details not available"
                : "Unique students enrolled"
            }
          />
          <StatCard
            title="Room utilization"
            icon={Building2}
            value={`${summary.rooms.average_fill}%`}
            detail={`Average seats filled across ${summary.rooms.used.toLocaleString()} rooms used`}
          />
          <StatCard
            title="Time slots used"
            icon={Clock}
            value={summary.calendar.slots_used.toLocaleString()}
            detail="Day and block pairs with at least one exam"
          />
        </div>
      </section>

      {groupCards.length > 0 && (
        <section aria-labelledby="stats-groups" className="space-y-3">
          <h2 id="stats-groups" className="pl-2 text-lg font-semibold">
            Exam groups and room constraints
          </h2>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {groupCards}
          </div>
        </section>
      )}

      <DistributionCharts calendar={summary.calendar} />
    </div>
  );
}
